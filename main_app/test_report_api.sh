#!/bin/bash

BASE_URL="http://localhost:8000"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Счетчики
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Функция для вывода результата теста
test_result() {
    local test_name="$1"
    local status="$2"
    local message="$3"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✓${NC} $test_name: $message"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗${NC} $test_name: $message"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

# Функция для проверки HTTP статуса
check_http_status() {
    local expected_status="$1"
    local actual_status="$2"
    local test_name="$3"
    
    if [ "$actual_status" -eq "$expected_status" ]; then
        test_result "$test_name" "PASS" "HTTP статус $actual_status (ожидался $expected_status)"
        return 0
    else
        test_result "$test_name" "FAIL" "HTTP статус $actual_status (ожидался $expected_status)"
        return 1
    fi
}

# Функция для проверки наличия jq
check_jq() {
    if ! command -v jq &> /dev/null; then
        echo -e "${YELLOW}Предупреждение: jq не установлен. JSON ответы не будут форматироваться.${NC}"
        echo "Установите jq для лучшего отображения: brew install jq (macOS) или apt-get install jq (Linux)"
        echo ""
        JQ_AVAILABLE=false
    else
        JQ_AVAILABLE=true
    fi
}

echo -e "${BLUE}=== Тестирование REST API эндпоинта /report ===${NC}"
echo ""

# Проверка доступности сервиса
echo -e "${BLUE}Проверка доступности сервиса...${NC}"
http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$BASE_URL/report" 2>/dev/null)
if [ -n "$http_code" ] && [ "$http_code" != "000" ]; then
    echo -e "${GREEN}✓ Сервис доступен (HTTP $http_code)${NC}"
    if [ "$http_code" -ge 500 ]; then
        echo -e "${YELLOW}⚠ Предупреждение: Сервис возвращает ошибку $http_code${NC}"
        echo "Проверьте логи приложения: docker-compose logs app"
    fi
else
    echo -e "${RED}✗ Сервис недоступен по адресу $BASE_URL${NC}"
    echo "Убедитесь, что приложение запущено: docker-compose up -d"
    exit 1
fi
echo ""

# Проверка наличия jq
check_jq

# Тест 1: Запрос без параметра date
echo -e "${BLUE}Тест 1: Запрос без параметра date (отчет за сегодня)${NC}"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/report" -H "Accept: application/json")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if check_http_status 200 "$http_code" "Тест 1.1: HTTP статус"; then
    if [ "$JQ_AVAILABLE" = true ]; then
        if echo "$body" | jq . > /dev/null 2>&1; then
            array_length=$(echo "$body" | jq 'length')
            if [ "$array_length" -ge 0 ]; then
                test_result "Тест 1.2: Валидный JSON массив" "PASS" "Массив содержит $array_length элементов"
                
                # Проверка структуры первого элемента (если есть)
                if [ "$array_length" -gt 0 ]; then
                    first_item=$(echo "$body" | jq '.[0]')
                    required_fields=("id" "report_at" "order_id" "count_product" "created_at")
                    all_fields_present=true
                    
                    for field in "${required_fields[@]}"; do
                        if ! echo "$first_item" | jq -e ".$field" > /dev/null 2>&1; then
                            all_fields_present=false
                            break
                        fi
                    done
                    
                    if [ "$all_fields_present" = true ]; then
                        test_result "Тест 1.3: Структура данных" "PASS" "Все обязательные поля присутствуют"
                    else
                        test_result "Тест 1.3: Структура данных" "FAIL" "Отсутствуют обязательные поля"
                    fi
                else
                    test_result "Тест 1.3: Структура данных" "PASS" "Массив пуст (нет отчетов за сегодня)"
                fi
            else
                test_result "Тест 1.2: Валидный JSON массив" "FAIL" "Ответ не является массивом"
            fi
        else
            test_result "Тест 1.2: Валидный JSON" "FAIL" "Ответ не является валидным JSON"
        fi
    else
        # Без jq - простая проверка
        if [[ "$body" == "["* ]]; then
            test_result "Тест 1.2: Формат ответа" "PASS" "Ответ начинается с '[' (массив)"
        else
            test_result "Тест 1.2: Формат ответа" "FAIL" "Ответ не является массивом"
        fi
    fi
fi
echo ""

# Тест 2: Запрос с параметром date (сегодняшняя дата)
echo -e "${BLUE}Тест 2: Запрос с параметром date (сегодняшняя дата)${NC}"
today=$(date +%Y-%m-%d)
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/report?report_date=$today" -H "Accept: application/json")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if check_http_status 200 "$http_code" "Тест 2.1: HTTP статус"; then
    if [ "$JQ_AVAILABLE" = true ]; then
        if echo "$body" | jq . > /dev/null 2>&1; then
            test_result "Тест 2.2: Валидный JSON" "PASS" "Ответ является валидным JSON"
            
            # Проверка, что все отчеты имеют правильную дату
            if echo "$body" | jq -e '.[]' > /dev/null 2>&1; then
                wrong_dates=$(echo "$body" | jq -r ".[] | select(.report_at != \"$today\") | .report_at" | wc -l | tr -d ' ')
                if [ "$wrong_dates" -eq 0 ]; then
                    test_result "Тест 2.3: Корректность даты" "PASS" "Все отчеты имеют дату $today"
                else
                    test_result "Тест 2.3: Корректность даты" "FAIL" "Найдены отчеты с неправильной датой"
                fi
            fi
        else
            test_result "Тест 2.2: Валидный JSON" "FAIL" "Ответ не является валидным JSON"
        fi
    else
        test_result "Тест 2.2: Формат ответа" "PASS" "Ответ получен"
    fi
fi
echo ""

# Тест 3: Запрос с датой без отчетов
echo -e "${BLUE}Тест 3: Запрос с датой без отчетов${NC}"
future_date="2026-01-01"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/report?report_date=$future_date" -H "Accept: application/json")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if check_http_status 200 "$http_code" "Тест 3.1: HTTP статус"; then
    if [ "$JQ_AVAILABLE" = true ]; then
        if echo "$body" | jq . > /dev/null 2>&1; then
            array_length=$(echo "$body" | jq 'length')
            if [ "$array_length" -eq 0 ]; then
                test_result "Тест 3.2: Пустой массив" "PASS" "Возвращен пустой массив для даты без отчетов"
            else
                test_result "Тест 3.2: Пустой массив" "FAIL" "Ожидался пустой массив, получено $array_length элементов"
            fi
        else
            if [ "$body" = "[]" ]; then
                test_result "Тест 3.2: Пустой массив" "PASS" "Возвращен пустой массив"
            else
                test_result "Тест 3.2: Пустой массив" "FAIL" "Ожидался пустой массив"
            fi
        fi
    else
        if [ "$body" = "[]" ]; then
            test_result "Тест 3.2: Пустой массив" "PASS" "Возвращен пустой массив"
        else
            test_result "Тест 3.2: Пустой массив" "FAIL" "Ожидался пустой массив, получено: $body"
        fi
    fi
fi
echo ""

# Тест 4: Проверка структуры JSON ответа
echo -e "${BLUE}Тест 5: Проверка структуры JSON ответа${NC}"
response=$(curl -s "$BASE_URL/report?report_date=$today" -H "Accept: application/json")

if [ "$JQ_AVAILABLE" = true ]; then
    if echo "$response" | jq . > /dev/null 2>&1; then
        array_length=$(echo "$response" | jq 'length')
        
        if [ "$array_length" -gt 0 ]; then
            first_item=$(echo "$response" | jq '.[0]')
            required_fields=("id" "report_at" "order_id" "count_product" "created_at")
            missing_fields=()
            
            for field in "${required_fields[@]}"; do
                if ! echo "$first_item" | jq -e ".$field" > /dev/null 2>&1; then
                    missing_fields+=("$field")
                fi
            done
            
            if [ ${#missing_fields[@]} -eq 0 ]; then
                test_result "Тест 4.1: Наличие обязательных полей" "PASS" "Все поля присутствуют: ${required_fields[*]}"
            else
                test_result "Тест 4.1: Наличие обязательных полей" "FAIL" "Отсутствуют поля: ${missing_fields[*]}"
            fi
            
            # Проверка типов данных
            id_type=$(echo "$first_item" | jq -r '.id | type')
            order_id_type=$(echo "$first_item" | jq -r '.order_id | type')
            count_type=$(echo "$first_item" | jq -r '.count_product | type')
            report_at_type=$(echo "$first_item" | jq -r '.report_at | type')
            created_at_type=$(echo "$first_item" | jq -r '.created_at | type')
            
            types_correct=true
            if [ "$id_type" != "number" ]; then types_correct=false; fi
            if [ "$order_id_type" != "number" ]; then types_correct=false; fi
            if [ "$count_type" != "number" ]; then types_correct=false; fi
            if [ "$report_at_type" != "string" ]; then types_correct=false; fi
            if [ "$created_at_type" != "string" ]; then types_correct=false; fi
            
            if [ "$types_correct" = true ]; then
                test_result "Тест 4.2: Типы данных" "PASS" "Все типы данных корректны"
            else
                test_result "Тест 4.2: Типы данных" "FAIL" "Некорректные типы: id=$id_type, order_id=$order_id_type, count=$count_type, report_at=$report_at_type, created_at=$created_at_type"
            fi
        else
            test_result "Тест 4.1: Наличие обязательных полей" "PASS" "Нет данных для проверки (массив пуст)"
        fi
    else
        test_result "Тест 4.1: Валидный JSON" "FAIL" "Ответ не является валидным JSON"
    fi
else
    test_result "Тест 4: Структура JSON" "PASS" "Пропущено (jq не установлен)"
fi
echo ""

# Тест 6: Проверка заголовков ответа
echo -e "${BLUE}Тест 5: Проверка HTTP заголовков${NC}"
content_type=$(curl -s -I "$BASE_URL/report?report_date=$today" -H "Accept: application/json" 2>/dev/null | grep -i "content-type" | cut -d' ' -f2 | tr -d '\r')

if [[ "$content_type" == *"application/json"* ]]; then
    test_result "Тест 5.1: Content-Type заголовок" "PASS" "Content-Type: $content_type"
else
    # Попробуем получить из ответа
    content_type=$(curl -s -D - "$BASE_URL/report?report_date=$today" -H "Accept: application/json" 2>/dev/null | grep -i "content-type" | cut -d' ' -f2 | tr -d '\r')
    if [[ "$content_type" == *"application/json"* ]]; then
        test_result "Тест 5.1: Content-Type заголовок" "PASS" "Content-Type: $content_type"
    else
        test_result "Тест 5.1: Content-Type заголовок" "FAIL" "Ожидался application/json, получено: $content_type"
    fi
fi
echo ""

# Итоговая статистика
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}=== ИТОГОВАЯ СТАТИСТИКА ТЕСТОВ ===${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Всего тестов выполнено: ${BLUE}$TOTAL_TESTS${NC}"
echo -e "${GREEN}Успешно пройдено: $PASSED_TESTS${NC}"
echo -e "${RED}Провалено: $FAILED_TESTS${NC}"
echo ""

# Расчет процента успешности
if [ "$TOTAL_TESTS" -gt 0 ]; then
    success_rate=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    echo -e "Процент успешности: ${BLUE}${success_rate}%${NC}"
    echo ""
    
    if [ "$FAILED_TESTS" -eq 0 ]; then
        echo -e "${GREEN}╔════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║  ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО! ✓  ║${NC}"
        echo -e "${GREEN}╚════════════════════════════════════╝${NC}"
        exit 0
    else
        echo -e "${RED}╔════════════════════════════════════╗${NC}"
        echo -e "${RED}║  НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ ✗      ║${NC}"
        echo -e "${RED}╚════════════════════════════════════╝${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}Не было выполнено ни одного теста${NC}"
    exit 1
fi

