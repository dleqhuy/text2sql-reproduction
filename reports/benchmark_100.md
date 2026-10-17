# Benchmark 100 câu Spider dev — 17/10/2026

Đã hoàn thành cả bốn method trên cùng 100 IDs của manifest [spider-v1](../data/splits/spider-v1.json). Model cấu hình: `cx/gpt-6-luna`; không training. Đây là subset 20 DB, không phải full Spider dev hoặc tái lập điểm paper gốc.

## Kết quả

| Method | Test Suite đúng/100 | DB gốc đúng/100 | SQL valid/100 | API requests | Mean inference (s/câu) |
|---|---:|---:|---:|---:|---:|
| Vanilla | 69 | 81 | 100 | 100 | 1.95 |
| DAIL-SQL | 76 | 87 | 100 | 200 | 4.02 |
| DIN-SQL | 78 | 86 | 96 | 400 | 8.33 |
| MAC-SQL | 73 | 86 | 100 | 125 | 3.44 |

Primary metric dùng comparison engine official `taoyds/test-suite-sql-eval`, commit `e97acc546ecbee8fa27fa8dbf025ef61493a876c`, trên 695 original/generated SQLite files: plug_value=false, keep_distinct=true, seed=42. Cột DB gốc dùng cùng engine nhưng chỉ một DB/schema. Không dùng parser legacy bị lỗi backtick để kết luận quality.

Mẫu số luôn 100, kể cả API/parse/SQL failures. DAIL cộng cả preliminary + final calls/tokens/latency; không bật self-consistency. Latency DAIL chưa gồm linking/retrieval offline. Các run có thời gian chồng lấp nên latency chỉ mô tả run này, không phải benchmark throughput độc lập.

## Protocol và nguồn

- Sampling DB-balanced round-robin, seed 42; difficulty theo official legacy hardness function trên gold AST: {'hard': 20, 'medium': 41, 'extra': 17, 'easy': 22}. Không dùng hardness/gold trong prompts.
- Smoke 10 là tập con của main 100 và đã dùng để sửa output-format handling; main không phải holdout độc lập. Không tinh chỉnh prompt theo gold main.
- Cùng model/temperature=0/retry policy. Token caps giữ stage settings: Vanilla/MAC 1024; DIN 600 generation, 350 correction; DAIL 200/call.
- Dữ liệu gốc và generated suites được pin hash: [Spider](../configs/spider_source.json), [test suite](../configs/test_suite_source.json). Gold self-check toàn bộ 100 IDs trên suites đã pass.
- DAIL dùng CoreNLP tokenizer gốc, cache LIKE tương đương đã kiểm chứng, MPNet revision pin; không allocate GloVe vectors không được code sử dụng. DIN có fallback original question khi NESTED thiếu subquestions; MAC nhận plain/fenced SQL. Xem [audit](../docs/repo_audit.md).
- Root/upstream envs được pin. Chưa kiểm chứng cold setup trên máy/platform khác. Không thêm per-run snapshot/diff source theo yêu cầu người dùng.

## Usage ghi nhận

| Method | Prompt tokens | Completion tokens | Usage coverage |
|---|---:|---:|---:|
| Vanilla | 268458 | 5727 | 100/100 prompt, 100/100 completion |
| DAIL-SQL | 648811 | 14300 | 100/100 prompt, 100/100 completion |
| DIN-SQL | 1873670 | 30210 | 100/100 prompt, 100/100 completion |
| MAC-SQL | 524885 | 10216 | 100/100 prompt, 100/100 completion |

Token sums là usage provider, chưa trừ cache discount; không suy ra chi phí tiền khi chưa có giá provider được xác minh.

## Phân tích 8 trường hợp lỗi

Chọn có quy tắc: ưu tiên lỗi pipeline hoặc câu đúng trên DB gốc nhưng không qua neighbor suites, rồi phủ DB khác nhau. Đây là case studies, không phải ước lượng tỷ trọng nguyên nhân trên toàn Spider.

### dev_000062 — pets_1 (extra)

What major is every student who does not own a cat as a pet, and also how old are they?

Gold:
```sql
SELECT major ,  age FROM student WHERE stuid NOT IN (SELECT T1.stuid FROM student AS T1 JOIN has_pet AS T2 ON T1.stuid  =  T2.stuid JOIN pets AS T3 ON T3.petid  =  T2.petid WHERE T3.pettype  =  'cat')
```

| Method | DB gốc | Test Suite | Status |
|---|---|---|---|
| Vanilla | đúng | đúng | ok/ok |
| DAIL-SQL | đúng | đúng | ok/ok |
| DIN-SQL | sai | sai | ok/sql_error |
| MAC-SQL | đúng | đúng | ok/ok |

Quan sát: có output không execute được hoặc lỗi pipeline; case vẫn ở mẫu số, không loại khỏi score.

Đối chiếu SQL: DIN có prefix SELECT trước Markdown fence, khiến SQL không hợp lệ. Đây là lỗi format adapter/output, chưa phải bằng chứng sai logic NOT EXISTS bên trong.

DIN-SQL — prediction chưa qua test suite:
````sql
SELECT ```sql SELECT Student.Major, Student.Age FROM Student WHERE NOT EXISTS (     SELECT 1     FROM Has_Pet     JOIN Pets ON Has_Pet.PetID = Pets.PetID     WHERE Has_Pet.StuID = Student.StuID       AND Pets.PetType = 'cat' ); ```
````

### dev_000226 — flight_2 (extra)

What is the airport code of the airport with the most flights?

Gold:
```sql
SELECT T1.AirportCode FROM AIRPORTS AS T1 JOIN FLIGHTS AS T2 ON T1.AirportCode  =  T2.DestAirport OR T1.AirportCode  =  T2.SourceAirport GROUP BY T1.AirportCode ORDER BY count(*) DESC LIMIT 1
```

| Method | DB gốc | Test Suite | Status |
|---|---|---|---|
| Vanilla | sai | sai | ok/ok |
| DAIL-SQL | sai | sai | ok/ok |
| DIN-SQL | sai | sai | ok/sql_error |
| MAC-SQL | sai | sai | ok/ok |

Quan sát: có output không execute được hoặc lỗi pipeline; case vẫn ở mẫu số, không loại khỏi score.

Đối chiếu SQL: DIN có lỗi SELECT trước fence. Ba method còn lại dùng UNION ALL để đếm hai đầu chuyến bay; gold dùng JOIN với OR, có thể khác multiplicity khi hai đầu trùng nhau. Đây là khác biệt cấu trúc cần kiểm tra ở DB counterexample, chưa xác nhận nguyên nhân duy nhất.

Vanilla — prediction chưa qua test suite:
````sql
SELECT AirportCode
FROM (
  SELECT AirportCode, COUNT(*) AS flight_count
  FROM (
    SELECT SourceAirport AS AirportCode FROM flights
    UNION ALL
    SELECT DestAirport AS AirportCode FROM flights
  )
  GROUP BY AirportCode
  ORDER BY flight_count DESC
  LIMIT 1
);
````

DAIL-SQL — prediction chưa qua test suite:
````sql
SELECT AirportCode
FROM (
    SELECT SourceAirport AS AirportCode FROM flights
    UNION ALL
    SELECT DestAirport AS AirportCode FROM flights
)
GROUP BY AirportCode
ORDER BY COUNT(*) DESC
LIMIT 1;
````

DIN-SQL — prediction chưa qua test suite:
````sql
SELECT ```sql SELECT AirportCode FROM (     SELECT SourceAirport AS AirportCode FROM flights     UNION ALL     SELECT DestAirport AS AirportCode FROM flights ) GROUP BY AirportCode ORDER BY COUNT(*) DESC LIMIT 1; ```
````

MAC-SQL — prediction chưa qua test suite:
````sql
SELECT AirportCode
FROM (
  SELECT SourceAirport AS AirportCode FROM flights
  UNION ALL
  SELECT DestAirport AS AirportCode FROM flights
)
GROUP BY AirportCode
ORDER BY COUNT(*) DESC
LIMIT 1;
````

### dev_000410 — course_teach (hard)

What are the names of the teachers whose courses have not been arranged?

Gold:
```sql
SELECT Name FROM teacher WHERE Teacher_id NOT IN (SELECT Teacher_id FROM course_arrange)
```

| Method | DB gốc | Test Suite | Status |
|---|---|---|---|
| Vanilla | đúng | đúng | ok/ok |
| DAIL-SQL | đúng | đúng | ok/ok |
| DIN-SQL | sai | sai | ok/sql_error |
| MAC-SQL | đúng | đúng | ok/ok |

Quan sát: có output không execute được hoặc lỗi pipeline; case vẫn ở mẫu số, không loại khỏi score.

Đối chiếu SQL: DIN có SELECT trước fence nên không execute được; không thể kết luận LEFT JOIN anti-join bên trong sai ngữ nghĩa chỉ từ score này.

DIN-SQL — prediction chưa qua test suite:
````sql
SELECT ```sql SELECT DISTINCT teacher.Name FROM teacher LEFT JOIN course_arrange   ON teacher.Teacher_ID = course_arrange.Teacher_ID WHERE course_arrange.Teacher_ID IS NULL; ```
````

### dev_000857 — orchestra (hard)

What are the record companies that are used by both orchestras founded before 2003 and those founded after 2003?

Gold:
```sql
SELECT Record_Company FROM orchestra WHERE Year_of_Founded  <  2003 INTERSECT SELECT Record_Company FROM orchestra WHERE Year_of_Founded  >  2003
```

| Method | DB gốc | Test Suite | Status |
|---|---|---|---|
| Vanilla | đúng | đúng | ok/ok |
| DAIL-SQL | đúng | đúng | ok/ok |
| DIN-SQL | sai | sai | ok/sql_error |
| MAC-SQL | đúng | đúng | ok/ok |

Quan sát: có output không execute được hoặc lỗi pipeline; case vẫn ở mẫu số, không loại khỏi score.

Đối chiếu SQL: DIN có SELECT trước fence; SQL lỗi format trước khi evaluator có thể kiểm tra aggregation/HAVING bên trong.

DIN-SQL — prediction chưa qua test suite:
````sql
SELECT ```sql SELECT Record_Company FROM orchestra WHERE Year_of_Founded < 2003 OR Year_of_Founded > 2003 GROUP BY Record_Company HAVING SUM(CASE WHEN Year_of_Founded < 2003 THEN 1 ELSE 0 END) > 0    AND SUM(CASE WHEN Year_of_Founded > 2003 THEN 1 ELSE 0 END) > 0; ```
````

### dev_000012 — concert_singer (hard)

List all song names by singers above the average age.

Gold:
```sql
SELECT song_name FROM singer WHERE age  >  (SELECT avg(age) FROM singer)
```

| Method | DB gốc | Test Suite | Status |
|---|---|---|---|
| Vanilla | đúng | đúng | ok/ok |
| DAIL-SQL | đúng | đúng | ok/ok |
| DIN-SQL | đúng | sai | ok/ok |
| MAC-SQL | đúng | đúng | ok/ok |

Quan sát: có lời giải đúng trên dữ liệu gốc nhưng không tương đương trên ít nhất một generated DB. Đây là lý do cần metric test-suite thay vì chỉ execution trên một DB.

Đối chiếu SQL: DIN thêm DISTINCT trong khi gold giữ duplicates. Với keep_distinct=true, khác biệt multiplicity có thể hiện trên generated DB dù DB gốc trả cùng kết quả.

DIN-SQL — prediction chưa qua test suite:
````sql
SELECT DISTINCT Song_Name FROM singer WHERE Age > (SELECT AVG(Age) FROM singer);
````

### dev_000105 — car_1 (hard)

How many car makers are there in each continents? List the continent name and the count.

Gold:
```sql
SELECT T1.Continent ,  count(*) FROM CONTINENTS AS T1 JOIN COUNTRIES AS T2 ON T1.ContId  =  T2.continent JOIN car_makers AS T3 ON T2.CountryId  =  T3.Country GROUP BY T1.Continent;
```

| Method | DB gốc | Test Suite | Status |
|---|---|---|---|
| Vanilla | sai | sai | ok/ok |
| DAIL-SQL | đúng | sai | ok/ok |
| DIN-SQL | đúng | đúng | ok/ok |
| MAC-SQL | đúng | sai | ok/ok |

Quan sát: có lời giải đúng trên dữ liệu gốc nhưng không tương đương trên ít nhất một generated DB. Đây là lý do cần metric test-suite thay vì chỉ execution trên một DB.

Đối chiếu SQL: Các prediction khác gold ở grouping theo ID so với tên Continent; Vanilla còn đổi JOIN thành LEFT JOIN và COUNT(*) thành COUNT(DISTINCT Id). Cần xét cả nhóm trùng tên và số dòng join, không chỉ tên cột output.

Vanilla — prediction chưa qua test suite:
````sql
SELECT continents.Continent, COUNT(DISTINCT car_makers.Id) AS maker_count
FROM continents
LEFT JOIN countries ON countries.Continent = continents.ContId
LEFT JOIN car_makers ON car_makers.Country = countries.CountryId
GROUP BY continents.ContId, continents.Continent;
````

DAIL-SQL — prediction chưa qua test suite:
````sql
SELECT continents.Continent, COUNT(*) AS maker_count
FROM continents
JOIN countries ON continents.ContId = countries.Continent
JOIN car_makers ON countries.CountryId = car_makers.Country
GROUP BY continents.ContId;
````

MAC-SQL — prediction chưa qua test suite:
````sql
SELECT continents.`Continent`, COUNT(car_makers.`Id`)
FROM continents
JOIN countries ON continents.`ContId` = countries.`Continent`
JOIN car_makers ON countries.`CountryId` = car_makers.`Country`
GROUP BY continents.`ContId`, continents.`Continent`;
````

### dev_000283 — employee_hire_evaluation (extra)

What is the name of the shop that is hiring the largest number of employees?

Gold:
```sql
SELECT t2.name FROM hiring AS t1 JOIN shop AS t2 ON t1.shop_id  =  t2.shop_id GROUP BY t1.shop_id ORDER BY count(*) DESC LIMIT 1
```

| Method | DB gốc | Test Suite | Status |
|---|---|---|---|
| Vanilla | đúng | đúng | ok/ok |
| DAIL-SQL | đúng | sai | ok/ok |
| DIN-SQL | đúng | đúng | ok/ok |
| MAC-SQL | đúng | đúng | ok/ok |

Quan sát: có lời giải đúng trên dữ liệu gốc nhưng không tương đương trên ít nhất một generated DB. Đây là lý do cần metric test-suite thay vì chỉ execution trên một DB.

Đối chiếu SQL: DAIL dùng COUNT(Employee_ID), gold dùng COUNT(*). COUNT(column) bỏ NULL; đây là khác biệt ngữ nghĩa có thể làm đổi thứ tự. Chưa cô lập nguyên nhân từ counterexample, kể cả tie ở LIMIT 1.

DAIL-SQL — prediction chưa qua test suite:
````sql
SELECT s.Name
FROM shop AS s
JOIN hiring AS h ON h.Shop_ID = s.Shop_ID
GROUP BY s.Shop_ID, s.Name
ORDER BY COUNT(h.Employee_ID) DESC
LIMIT 1;
````

### dev_000373 — cre_Doc_Template_Mgt (extra)

What is the document id and name with greatest number of paragraphs?

Gold:
```sql
SELECT T1.document_id ,  T2.document_name FROM Paragraphs AS T1 JOIN Documents AS T2 ON T1.document_id  =  T2.document_id GROUP BY T1.document_id ORDER BY count(*) DESC LIMIT 1
```

| Method | DB gốc | Test Suite | Status |
|---|---|---|---|
| Vanilla | đúng | sai | ok/ok |
| DAIL-SQL | đúng | sai | ok/ok |
| DIN-SQL | đúng | đúng | ok/ok |
| MAC-SQL | đúng | sai | ok/ok |

Quan sát: có lời giải đúng trên dữ liệu gốc nhưng không tương đương trên ít nhất một generated DB. Đây là lý do cần metric test-suite thay vì chỉ execution trên một DB.

Đối chiếu SQL: Vanilla/MAC dùng COUNT(Paragraph_ID) thay COUNT(*); Vanilla còn dùng LEFT JOIN. DAIL gần cấu trúc gold nhưng thêm tên vào GROUP BY. Các sai khác và tie khi LIMIT 1 cần được kiểm tra riêng, không suy ra nguyên nhân duy nhất từ score.

Vanilla — prediction chưa qua test suite:
````sql
SELECT d.Document_ID, d.Document_Name
FROM Documents AS d
LEFT JOIN Paragraphs AS p ON p.Document_ID = d.Document_ID
GROUP BY d.Document_ID, d.Document_Name
ORDER BY COUNT(p.Paragraph_ID) DESC
LIMIT 1;
````

DAIL-SQL — prediction chưa qua test suite:
````sql
SELECT T1.Document_ID, T1.Document_Name
FROM Documents AS T1
JOIN Paragraphs AS T2 ON T1.Document_ID = T2.Document_ID
GROUP BY T1.Document_ID, T1.Document_Name
ORDER BY COUNT(*) DESC
LIMIT 1;
````

MAC-SQL — prediction chưa qua test suite:
````sql
SELECT d.`Document_ID`, d.`Document_Name`
FROM Documents AS d
JOIN Paragraphs AS p ON p.`Document_ID` = d.`Document_ID`
GROUP BY d.`Document_ID`, d.`Document_Name`
ORDER BY COUNT(p.`Paragraph_ID`) DESC
LIMIT 1;
````

## Artifacts và tái lập

Mỗi run dưới có predictions, events/raw responses, checkpoints, config/provenance và hai thư mục evaluation với hashes/config/metrics:

- Vanilla: `runs/spider-v1-main-vanilla/`.
- DAIL-SQL: `runs/spider-v1-main-dail/`.
- DIN-SQL: `runs/spider-v1-main-din/`.
- MAC-SQL: `runs/spider-v1-main-mac/`.
- DAIL parent runs: `runs/spider-v1-main-dail-preliminary/`, `runs/spider-v1-main-dail-final/`; aggregate chỉ giữ final SQL và cộng accounting, không rewrite outputs gốc.
- [Machine-readable comparison](comparison.json), [commands](../docs/reproducibility.md), [implementation status](../docs/implementation/status.md).

Inference/evaluation/report trên máy hiện tại đã hoàn tất. Việc đọc thêm các raw stages để phân tích sâu hoặc mở rộng full-dev là experiment tiếp theo, không nằm trong các score ở đây.
