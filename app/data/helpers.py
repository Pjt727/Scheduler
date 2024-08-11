RED = '\033[91m'
GREEN = '\033[92m'
BLUE = '\033[94m'
END = '\033[0m'
# ]]]] -- my editor wants me to close these :O

def print_success(message: str) -> None:
    print(GREEN + message + END)

def print_error(message: str) -> None:
    print(RED + message + END)

def print_info(message: str) -> None:
    print(BLUE + message + END)


