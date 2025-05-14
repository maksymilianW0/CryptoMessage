import shlex
from typing import List, Any, Optional, Callable, Dict, Tuple


# ======= Niestandardowe wyjątki =======
# Definicje wyjątków związanych z obsługą argumentów i komend
class ArgumentError(ValueError):
    """Błąd związany z argumentami."""
    pass

class UnknownCommandError(ValueError):
    """Błąd wywołany przez nieznaną komendę."""
    pass


# ======= Klasa Argument =======
# Klasa reprezentująca pojedynczy argument lub flagę komendy
class Argument:
    def __init__(
        self,
        *names: str,  # Nazwy flag, np. "-v", "--verbose"
        ID: str,  # Unikalny identyfikator argumentu (przekazywany do funkcji)
        arg_type: Optional[Callable[[str], Any]] = str,  # Funkcja konwertująca tekstową wartość na właściwy typ (domyślnie str)
        default: Optional[Any] = None,  # Wartość domyślna, jeśli wartość nie zostanie podana
        unset_default: Optional[Any] = None,  # Wartość, gdy argument nie zostanie ustawiony
        help: Optional[str] = None,  # Opis argumentu
        choices: Optional[List[Any]] = None,  # Dozwolone wartości dla argumentu
        required: bool = False,  # Czy argument jest wymagany
        positional: bool = False  # Czy argument jest pozycyjny (bez flagi)
    ):
        self.names: Tuple[str, ...] = names  # Lista nazw flag
        self.ID: str = ID
        self.arg_type: Optional[Callable[[str], Any]] = arg_type
        self.default: Optional[Any] = default
        self.unset_default: Optional[Any] = unset_default
        self.help: Optional[str] = help
        self.choices: Optional[List[Any]] = choices
        self.required: bool = required
        self.positional: bool = positional

    def parse(self, value: Optional[str]) -> Any:
        """
        Konwertuje tekstową wartość argumentu na właściwy typ.
        Dla flag typu bool (przełączników) zwraca True.
        """
        if self.arg_type == bool:
            return True

        if value is None:
            return None

        try:
            # Próba konwersji wartości przy użyciu wskazanej funkcji
            converted = self.arg_type(value)
        except Exception as e:
            # Rzucamy wyjątek w przypadku nieudanej konwersji
            raise ArgumentError(f"Błąd konwersji argumentu '{self.ID}' z wartością '{value}': {e}")

        # Jeśli określono dozwolone wybory, sprawdzamy, czy wartość do nich należy
        if self.choices and converted not in self.choices:
            raise ArgumentError(f"Wartość argumentu '{self.ID}' musi być jedną z: {self.choices}")

        return converted


# ======= Klasa Arguments =======
# Klasa zarządzająca zestawem argumentów dla danej komendy
class Arguments:
    def __init__(self):
        self.args: List[Argument] = []  # Lista wszystkich argumentów
        self.flag_map: Dict[str, Argument] = {}  # Mapa nazw flag do obiektów Argument

    def add_argument(
        self,
        *names: str,  # Nazwy flag, np. "-v", "--verbose"
        ID: str,
        arg_type: Optional[Callable[[str], Any]] = str,
        default: Optional[Any] = None,
        unset_default: Optional[Any] = None,
        help: Optional[str] = None,
        choices: Optional[List[Any]] = None,
        required: bool = False,
        positional: bool = False  # Określa, czy argument jest pozycyjny
    ) -> None:
        # Tworzymy nowy obiekt Argument
        new_arg = Argument(
            *names,
            ID=ID,
            arg_type=arg_type,
            default=default,
            unset_default=unset_default,
            help=help,
            choices=choices,
            required=required,
            positional=positional
        )
        self.args.append(new_arg)

        # Jeśli argument nie jest pozycyjny, mapujemy wszystkie jego nazwy (flag) do obiektu Argument
        if not positional:
            for name in names:
                self.flag_map[name] = new_arg  

    def parse_arguments(self, tokens: List[str]) -> Dict[str, Any]:
        """
        Parsuje listę tokenów (wynik shlex.split) i zwraca słownik, gdzie kluczem jest ID argumentu,
        a wartością – przekonwertowana wartość.
        """
        parsed: Dict[str, Any] = {}
        index = 0  # Indeks aktualnie przetwarzanego tokena
        # Pobieramy listę argumentów pozycyjnych
        positional_args = [arg for arg in self.args if arg.positional]
        positional_index = 0

        while index < len(tokens):
            token = tokens[index]

            # Obsługa połączonych flag boolowskich, np. "-xpr"
            if token.startswith("-") and not token.startswith("--") and len(token) > 2:
                # Rozbijamy token na pojedyncze flagi, np. "-xpr" → ['-x', '-p', '-r']
                expanded_flags = ["-" + c for c in token[1:]]

                # Sprawdzamy, czy wszystkie flagi mają typ bool
                if all(flag in self.flag_map and self.flag_map[flag].arg_type == bool for flag in expanded_flags):
                    # Zamieniamy token na listę pojedynczych flag
                    tokens[index:index + 1] = expanded_flags
                    continue  # Kontynuujemy pętlę, aby przetworzyć nowe tokeny
                else:
                    # Jeśli którakolwiek flaga nie jest typu bool, nie można ich połączyć – rzucamy błąd
                    invalid_flags = [flag for flag in expanded_flags if flag not in self.flag_map or self.flag_map[flag].arg_type != bool]
                    raise ValueError(f"Nie można połączyć flag {', '.join(invalid_flags)} – wymagają wartości.")

            # Jeśli token pasuje do zdefiniowanej flagi
            if token in self.flag_map:
                arg = self.flag_map[token]
                if arg.arg_type != bool:
                    # Jeśli argument nie jest typu bool, oczekujemy, że kolejny token będzie jego wartością
                    if index + 1 < len(tokens) and tokens[index + 1] not in self.flag_map:
                        value = arg.parse(tokens[index + 1])
                        index += 1  # Pomijamy token, który był wartością
                    else:
                        # Jeżeli brak wartości i argument jest wymagany, rzucamy wyjątek
                        if arg.required and arg.default is None:
                            raise ArgumentError(f"Brak wartości dla argumentu '{token}'.")
                        value = arg.default
                else:
                    # Dla flag typu bool wartość to True
                    value = True
                parsed[arg.ID] = value

            # Jeśli token nie jest flagą, przypisujemy go do argumentu pozycyjnego
            elif positional_index < len(positional_args):
                parsed[positional_args[positional_index].ID] = positional_args[positional_index].parse(token)
                positional_index += 1

            else:
                # Token nie pasuje ani do flag, ani do argumentów pozycyjnych – zgłaszamy błąd
                raise ArgumentError(f"Nieoczekiwany argument: {token}")

            index += 1

        # Uzupełniamy słownik wynikowy wartościami domyślnymi dla argumentów, które nie zostały podane
        for arg in self.args:
            if arg.ID not in parsed:
                if arg.required:
                    raise ArgumentError(f"Brak wymaganego argumentu: {arg.ID}")
                parsed[arg.ID] = arg.unset_default

        return parsed


# ======= Klasa Command =======
# Klasa reprezentująca komendę z przypisaną funkcją i opcjonalnym zestawem argumentów
class Command:
    def __init__(self, *names: str, func: Callable[..., Any], arguments: Optional[Arguments] = None):
        self.names: Tuple[str, ...] = names  # Nazwy, pod którymi komenda będzie dostępna
        self.func: Callable[..., Any] = func  # Funkcja wywoływana przy wykonaniu komendy
        self.arguments: Optional[Arguments] = arguments  # Zestaw argumentów przypisanych do komendy


# ======= Klasa CommandParser =======
# Klasa zarządzająca rejestrowaniem i wykonywaniem komend
class CommandParser:
    def __init__(self):
        self.commands: List[Command] = []  # Lista zarejestrowanych komend
        self.command_map: Dict[str, Command] = {}  # Mapowanie nazwy komendy na obiekt Command

    def add_command(self, *names: str, func: Callable[..., Any], arguments: Optional[Arguments] = None) -> None:
        """
        Dodaje komendę do parsera.
        Każda z nazw komendy jest zapisywana w słowniku, co pozwala na szybkie wyszukiwanie.
        """
        new_command = Command(*names, func=func, arguments=arguments)
        self.commands.append(new_command)
        for name in names:
            self.command_map[name] = new_command  

    def execute(self, command_line: str) -> Any:
        """
        Parsuje podaną linię poleceń i wykonuje odpowiadającą komendę.
        1. Tokenizacja przy użyciu shlex.split (obsługa cudzysłowów).
        2. Wybór komendy na podstawie pierwszego tokena.
        3. Parsowanie argumentów (jeśli zdefiniowane).
        4. Wywołanie funkcji przypisanej do komendy z przekazanymi argumentami.
        """
        tokens = shlex.split(command_line)
        if not tokens:
            raise UnknownCommandError("Nie podano żadnej komendy.")

        command_name = tokens[0]      # Pierwszy token traktowany jest jako nazwa komendy
        arg_tokens = tokens[1:]       # Pozostałe tokeny to argumenty

        # Pobieramy komendę z mapy
        selected_command = self.command_map.get(command_name)
        if selected_command is None:
            raise UnknownCommandError(f"Nieznana komenda: {command_name}")

        parsed_args = {}
        # Jeżeli komenda ma zdefiniowane argumenty, dokonujemy ich parsowania
        if selected_command.arguments:
            parsed_args = selected_command.arguments.parse_arguments(arg_tokens)

        # Wywołujemy funkcję przypisaną do komendy z przekazanymi argumentami
        return selected_command.func(**parsed_args)