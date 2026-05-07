#!/bin/bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"

# Detect OS
OS="$(uname -s)"

# ---------- Docker ----------
install_docker_linux() {
    if command -v docker &> /dev/null; then
        echo "Docker already installed: $(docker --version)"
        return 0
    fi
    echo "Installing Docker via apt..."
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl gnupg
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
      https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
      | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    echo "Docker installed: $(docker --version)"
}

install_docker_macos() {
    if command -v docker &> /dev/null; then
        echo "Docker already installed: $(docker --version)"
        return 0
    fi
    if ! command -v brew &> /dev/null; then
        echo "ERROR: Homebrew is required to install Docker on macOS."
        echo "Install it from https://brew.sh then re-run this script."
        exit 1
    fi
    echo "Installing Docker Desktop via Homebrew..."
    brew install --cask docker
    echo "Docker Desktop installed. Please launch Docker Desktop from Applications before running integration tests."
}

echo "=== Installing Docker ==="
case "$OS" in
    Linux)  install_docker_linux ;;
    Darwin) install_docker_macos ;;
    *)      echo "ERROR: Unsupported OS: $OS"; exit 1 ;;
esac

# ---------- PostgreSQL ----------
install_postgres_linux() {
    if command -v psql &> /dev/null; then
        echo "PostgreSQL already installed: $(psql --version)"
    else
        echo "Installing PostgreSQL via apt..."
        sudo apt-get update
        sudo apt-get install -y postgresql postgresql-contrib
        echo "PostgreSQL installed: $(psql --version)"
    fi
    if ! sudo systemctl is-active --quiet postgresql; then
        sudo systemctl start postgresql
        sudo systemctl enable postgresql
    fi
}

install_postgres_macos() {
    # Homebrew postgresql@16 is keg-only; resolve the real binary path
    local pg_bin="/opt/homebrew/opt/postgresql@16/bin"
    if [ -x "$pg_bin/psql" ]; then
        echo "PostgreSQL already installed: $("$pg_bin/psql" --version)"
    elif command -v psql &> /dev/null; then
        echo "PostgreSQL already installed: $(psql --version)"
        pg_bin="$(dirname "$(command -v psql)")"
    else
        if ! command -v brew &> /dev/null; then
            echo "ERROR: Homebrew is required to install PostgreSQL on macOS."
            echo "Install it from https://brew.sh then re-run this script."
            exit 1
        fi
        echo "Installing PostgreSQL via Homebrew..."
        brew install postgresql@16
        echo "PostgreSQL installed: $("$pg_bin/psql" --version)"
    fi
    export PATH="$pg_bin:$PATH"
    if ! brew services list | grep -q "postgresql.*started"; then
        brew services start postgresql@16
    fi
}

setup_postgres_db() {
    echo "Setting up PostgreSQL database and user..."
    # Source .env for credentials (create from example if missing)
    if [ ! -f "$DIR/.env" ]; then
        echo "Creating .env from .env.example..."
        cp "$DIR/.env.example" "$DIR/.env"
    fi
    set -a
    # shellcheck disable=SC1091
    source "$DIR/.env"
    set +a

    # On Linux the postgres superuser needs sudo; on macOS Homebrew runs
    # as the current user so we call psql directly.
    local run_psql="$PSQL_CMD"

    # Create user if it does not exist
    if $run_psql -tAc \
        "SELECT 1 FROM pg_roles WHERE rolname='${POSTGRES_USER}'" \
        | grep -q 1; then
        echo "PostgreSQL user '${POSTGRES_USER}' already exists"
    else
        $run_psql -c \
            "CREATE USER ${POSTGRES_USER} WITH PASSWORD '${POSTGRES_PASSWORD}';"
        echo "Created PostgreSQL user '${POSTGRES_USER}'"
    fi

    # Drop and recreate database for a fresh state
    if $run_psql -tAc \
        "SELECT 1 FROM pg_database WHERE datname='${POSTGRES_DB}'" \
        | grep -q 1; then
        echo "Dropping existing database '${POSTGRES_DB}'..."
        $run_psql -c "DROP DATABASE ${POSTGRES_DB};"
    fi
    $run_psql -c \
        "CREATE DATABASE ${POSTGRES_DB} OWNER ${POSTGRES_USER};"
    echo "Created fresh PostgreSQL database '${POSTGRES_DB}'"
}

echo ""
echo "=== Installing PostgreSQL ==="
case "$OS" in
    Linux)
        install_postgres_linux
        PSQL_CMD="sudo -u postgres psql"
        setup_postgres_db
        ;;
    Darwin)
        install_postgres_macos
        PSQL_CMD="psql postgres"
        setup_postgres_db
        ;;
esac

echo ""
echo "=== Installing backend ==="
cd "$DIR/response-planner-backend"
pip install -e ".[test]"

echo ""
echo "=== Installing frontend ==="
cd "$DIR/response-planner-frontend"
# Load nvm if available (needed when running under non-interactive bash)
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
npm install

echo ""
echo "=== Installing integration test dependencies ==="
cd "$DIR/integration_tests"
npm install
npx playwright install --with-deps chromium

echo ""
echo "=== All dependencies installed ==="
