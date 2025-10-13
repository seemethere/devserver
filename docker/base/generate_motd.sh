#!/bin/sh

# Color Definitions
if [ -z "$DEVSERVER_TEST_MODE" ]; then
    C_RESET=$(printf '\033[0m')
    C_RED=$(printf '\033[0;31m')
    C_GREEN=$(printf '\033[0;32m')
    C_YELLOW=$(printf '\033[0;33m')
    C_BLUE=$(printf '\033[0;34m')
    C_MAGENTA=$(printf '\033[0;35m')
    C_CYAN=$(printf '\033[0;36m')
    C_BOLD=$(printf '\033[1m')
else
    # In test mode, disable colors
    C_RESET=""
    C_RED=""
    C_GREEN=""
    C_YELLOW=""
    C_BLUE=""
    C_MAGENTA=""
    C_CYAN=""
    C_BOLD=""
fi

# ASCII Art Logo
LOGO=$(cat << EOF
        ${C_CYAN}
        /////////////
      /////////////////
    ///////     ///////
   /////         /////
  /////   ${C_YELLOW}o o${C_CYAN}   /////
 /////   ${C_YELLOW}>${C_CYAN}     /////
 /////     ${C_YELLOW}^${C_CYAN}     /////
  /////         /////
   /////////////
    ///////////
EOF
)

# System Information Gathering
OS_INFO=$(lsb_release -ds 2>/dev/null || echo "Linux")
KERNEL=$(uname -r)
if command -v lscpu >/dev/null 2>&1; then
    CPU_INFO=$(lscpu | grep "Model name:" | sed 's/Model name:[[:space:]]*//')
else
    CPU_INFO=$(grep "model name" /proc/cpuinfo | head -n 1 | cut -d: -f2 | sed 's/^\s*//')
fi
CPU_CORES=$(grep -c ^processor /proc/cpuinfo)
MEM_INFO=$(free -h | awk '/^Mem:/ {print $3 "/" $2}')
DISK_INFO=$(df -h / | awk 'NR==2 {print $3 "/" $2 " (" $5 " used)"}')
UPTIME=$(uptime -p)

# Formatting
INFO_WIDTH=40
LOGO_WIDTH=25

print_line() {
    printf "${C_CYAN}%-${LOGO_WIDTH}s${C_RESET}  ${C_BOLD}%s${C_RESET}: %s\n" "$1" "$2" "$3"
}

# Combine Logo and System Info line by line
LOGO_LINES=$(printf "%s\n" "$LOGO" | sed "s/^/ /" | sed "s/$/ /")
INFO_LINES=$(
    {
        echo "${C_BOLD}${C_YELLOW}Welcome to your DevServer!${C_RESET}"
        echo
        printf "${C_GREEN}${C_BOLD}%-8s${C_RESET}: %s\n" "OS" "$OS_INFO"
        printf "${C_GREEN}${C_BOLD}%-8s${C_RESET}: %s\n" "Kernel" "$KERNEL"
        printf "${C_GREEN}${C_BOLD}%-8s${C_RESET}: %s\n" "CPU" "$CPU_INFO ($CPU_CORES cores)"
        printf "${C_GREEN}${C_BOLD}%-8s${C_RESET}: %s\n" "Memory" "$MEM_INFO"
        printf "${C_GREEN}${C_BOLD}%-8s${C_RESET}: %s\n" "Disk" "$DISK_INFO"
        printf "${C_GREEN}${C_BOLD}%-8s${C_RESET}: %s\n" "Uptime" "$UPTIME"
        echo
        echo "${C_YELLOW}Happy coding!${C_RESET}"
        echo
    }
)

# Using temp files for POSIX-compliant side-by-side printing with paste
LOGO_FILE=$(mktemp)
INFO_FILE=$(mktemp)

# Ensure temp files are removed on exit, even if the script fails
trap 'rm -f "$LOGO_FILE" "$INFO_FILE"' EXIT

printf "%s\n" "$LOGO_LINES" > "$LOGO_FILE"
printf "%s\n" "$INFO_LINES" > "$INFO_FILE"

# Combine the files line-by-line, manually calculating padding for perfect alignment.
# This is more robust than simple paste/awk as it correctly handles non-printing ANSI color codes.
paste -d'|' "$LOGO_FILE" "$INFO_FILE" | while IFS='|' read -r logo_line info_line; do
    # Strip ANSI color codes to calculate the visible-only width of the logo line.
    esc=$(printf '\033')
    visible_len=$(printf "%s" "$logo_line" | sed "s/${esc}\\[[0-9;]*m//g" | wc -c)

    # Calculate the exact number of padding spaces needed.
    padding_len=$((25 - visible_len))
    if [ $padding_len -lt 0 ]; then
        padding_len=0
    fi
    padding=$(printf "%${padding_len}s" "")

    # Print the logo line, the exact padding, and then the info line.
    printf "%s%s %s\n" "$logo_line" "$padding" "$info_line"
done
