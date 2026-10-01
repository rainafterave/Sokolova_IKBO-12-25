# Практическое занятие №1. Введение, основы работы в командной строке

**Цель:** научиться выполнять простые действия с файлами и каталогами в Linux из командной строки. Сравнить работу в командной строке Windows и Linux.

**Система:** Ubuntu (WSL), bash. Для проверки скриптов использовался ShellCheck.

## Задача 1

Вывести отсортированный в алфавитном порядке список имён пользователей в файле passwd (вам понадобится grep).

```text
WS-1C9B81CA:/mnt/host/c/Users/1# grep -o '^[^:]*' /etc/passwd | sort
bin
cron
daemon
ftp
games
guest
halt
lp
mail
news
nobody
ntp
root
shutdown
sshd
sync
uucp
```

## Задача 2

Вывести данные `/etc/protocols` в отформатированном и отсортированном порядке для 5 наибольших портов.

```text
WS-1C9B81CA:/mnt/host/c/Users/1# grep -v '^#' /etc/protocols | awk 'NF {print $2, $1}' | sort -nr | head -5
262 mptcp
143 ethernet
142 rohc
141 wesp
140 shim6
```

## Задача 3

Написать программу `banner` средствами bash для вывода текстов в рамке (размер баннера должен меняться!).

Скрипт `banner`:

```bash
#!/bin/bash
if [ $# -eq 0 ]; then
    echo "Usage: $0 text" >&2
    exit 1
fi

text="$*"
border=$(printf '%*s' "$(( ${#text} + 2 ))" '' | tr ' ' '-')

printf '+%s+\n' "$border"
printf '| %s |\n' "$text"
printf '+%s+\n' "$border"
```

Проверка:

```text
milena@WS-1C9B81CA:/mnt/c/Users/1$ chmod +x banner
milena@WS-1C9B81CA:/mnt/c/Users/1$ ./banner "Hello from RTU MIREA"
+----------------------+
| Hello from RTU MIREA |
+----------------------+
```

## Задача 4

Написать программу для вывода всех идентификаторов (по правилам C/C++ или Java) в файле без повторений.

Скрипт `identifiers`:

```bash
#!/usr/bin/env bash

if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then
    printf 'Использование: %s файл\n' "$0" >&2
    exit 1
fi

LC_ALL=C grep -oE '[A-Za-z_][A-Za-z0-9_]*' "$1" |
    LC_ALL=C sort -u |
    paste -sd ' ' -
```

Файл `hello.c`:

```c
#include <stdio.h>

int main(void) {
    printf("hello world\n");
    return 0;
}
```

Проверка:

```text
milena@WS-1C9B81CA:/mnt/c/Users/1$ chmod +x identifiers
milena@WS-1C9B81CA:/mnt/c/Users/1$ shellcheck identifiers
milena@WS-1C9B81CA:/mnt/c/Users/1$ ./identifiers hello.c
h hello include int main n printf return stdio void world
```

## Задача 5

Написать программу для регистрации пользовательской команды: задать правильные права доступа и скопировать её в `/usr/local/bin`.

Скрипт `reg`:

```bash
#!/bin/bash

if [ $# -ne 1 ]; then
    echo "Usage: $0 file" >&2
    exit 1
fi

if [ ! -f "$1" ]; then
    echo "Error: $1 not found" >&2
    exit 1
fi

sudo install -m 755 -- "$1" /usr/local/bin/ || exit 1
echo "$1 registered in /usr/local/bin"
```

Проверка:

```text
milena@WS-1C9B81CA:/mnt/c/Users/1$ chmod +x reg
milena@WS-1C9B81CA:/mnt/c/Users/1$ shellcheck reg
milena@WS-1C9B81CA:/mnt/c/Users/1$ ./reg banner
banner registered in /usr/local/bin
```

## Задача 6

Написать программу для проверки наличия комментария в первой строке файлов с расширением `c`, `js` и `py`.

Скрипт `check_comments`:

```bash
#!/bin/bash
dir="${1:-.}"

find "$dir" -type f \( -name '*.c' -o -name '*.js' -o -name '*.py' \) -print0 |
while IFS= read -r -d '' file; do
    first=$(head -n 1 "$file")

    case "$file" in
        *.py) pattern='^[[:space:]]*#' ;;
        *)    pattern='^[[:space:]]*(//|/\*)' ;;
    esac

    if [[ $first =~ $pattern ]]; then
        echo "$file: comment found"
    else
        echo "$file: NO comment"
    fi
done
```

Проверка:

```text
milena@WS-1C9B81CA:/mnt/c/Users/1$ chmod +x check_comments
milena@WS-1C9B81CA:/mnt/c/Users/1$ shellcheck check_comments
milena@WS-1C9B81CA:/mnt/c/Users/1$ ./check_comments hello.c
hello.c: NO comment
```

## Задача 7

Написать программу для нахождения файлов-дубликатов (имеющих одну или более копий содержимого) по заданному пути и в подкаталогах.

Скрипт `dubles`:

```bash
#!/usr/bin/env bash
dir="${1:-.}"

if [ ! -d "$dir" ]; then
    echo "Папка не найдена: $dir" >&2
    exit 1
fi

find "$dir" -type f -exec md5sum -- {} + |
    sort |
    uniq -w 32 --all-repeated=separate
```

Проверка:

```text
milena@WS-1C9B81CA:/mnt/c/Users/1$ mkdir task7_test
milena@WS-1C9B81CA:/mnt/c/Users/1$ printf 'одинаковый текст\n' > task7_test/a.txt
milena@WS-1C9B81CA:/mnt/c/Users/1$ cp task7_test/a.txt task7_test/b.txt
milena@WS-1C9B81CA:/mnt/c/Users/1$ chmod +x dubles
milena@WS-1C9B81CA:/mnt/c/Users/1$ shellcheck dubles
milena@WS-1C9B81CA:/mnt/c/Users/1$ ./dubles task7_test
def05c75ff22e5a17c17bdef69107a9c  task7_test/a.txt
def05c75ff22e5a17c17bdef69107a9c  task7_test/b.txt
```

## Задача 8

Написать программу, которая находит все файлы в данном каталоге с расширением, указанным в качестве аргумента, и архивирует эти файлы в архив tar.

Скрипт `arch`:

```bash
#!/bin/bash
ext="$1"

find . -maxdepth 1 -type f -name "*.$ext" -print0 |
    tar --null -cvf "archive_${ext}.tar" -T -
```

Проверка:

```text
milena@WS-1C9B81CA:/mnt/c/Users/1$ chmod +x arch
milena@WS-1C9B81CA:/mnt/c/Users/1$ shellcheck arch
milena@WS-1C9B81CA:/mnt/c/Users/1$ ./arch c
./hello.c
```

## Задача 9

Написать программу, которая заменяет в файле последовательности из 4 пробелов на символ табуляции. Входной и выходной файлы задаются аргументами.

Скрипт `spacetotub`:

```bash
#!/bin/bash

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 input output" >&2
    exit 1
fi

if [ "$1" = "$2" ]; then
    echo "Input and output must differ" >&2
    exit 1
fi

sed 's/ \{4\}/\t/g' "$1" > "$2"
```

Проверка:

```text
milena@WS-1C9B81CA:/mnt/c/Users/1$ chmod +x spacetotub
milena@WS-1C9B81CA:/mnt/c/Users/1$ shellcheck spacetotub
milena@WS-1C9B81CA:/mnt/c/Users/1$ ./spacetotub hello.c hello_new.c
```

## Задача 10

Написать программу, которая выводит названия всех пустых текстовых файлов в указанной директории. Директория передаётся в программу параметром.

Скрипт `emptytxt`:

```bash
#!/bin/bash

if [ "$#" -ne 1 ] || [ ! -d "$1" ]; then
    echo "Usage: $0 directory" >&2
    exit 1
fi

find "$1" -maxdepth 1 -type f -name '*.txt' -empty -printf '%f\n'
```

Проверка:

```text
milena@WS-1C9B81CA:/mnt/c/Users/1$ mkdir t
milena@WS-1C9B81CA:/mnt/c/Users/1$ touch t/e1.txt t/e2.txt
milena@WS-1C9B81CA:/mnt/c/Users/1$ chmod +x emptytxt
milena@WS-1C9B81CA:/mnt/c/Users/1$ shellcheck emptytxt
milena@WS-1C9B81CA:/mnt/c/Users/1$ ./emptytxt t
e1.txt
e2.txt
```

## Выводы

В ходе практического занятия была освоена работа в командной строке Ubuntu через WSL. Были созданы bash-скрипты для обработки текста, поиска файлов, создания архива и настройки прав доступа. Для решения задач использовались команды `grep`, `sort`, `awk`, `sed`, `find`, `tar` и другие утилиты. Скрипты проверялись с помощью ShellCheck.

Было изучено объединение команд в конвейер через `|`. Командная строка Windows использовалась для запуска WSL, а работа с файлами и скриптами выполнялась в Linux. Это позволило увидеть различия между двумя средами командной строки.
