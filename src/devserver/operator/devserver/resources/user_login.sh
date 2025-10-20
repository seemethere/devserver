#!/bin/sh

set -e

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

display_devserver_banner() {
    # Array of random messages
    MESSAGES="Happy coding!
    Have you committed your changes?
    Don't forget to take a break.
    The caffeine is strong with this one."

    # Select a random message
    NUM_MESSAGES=$(printf "%s" "$MESSAGES" | grep -c '^')
    RANDOM_INDEX=$(awk -v n="$NUM_MESSAGES" 'BEGIN{srand(); print int(rand()*n)+1}')
    RANDOM_MESSAGE=$(printf "%s" "$MESSAGES" | sed -n "${RANDOM_INDEX}p")

    # Define message width and wrap the message
    MESSAGE_WIDTH=20
    WRAPPED_MESSAGE=$(printf "%s" "$RANDOM_MESSAGE" | fold -s -w "$MESSAGE_WIDTH")

    # System Information Gathering
    OS_INFO=$(grep -E '^PRETTY_NAME=' /etc/os-release | sed -e 's/PRETTY_NAME=//' -e 's/"//g' 2>/dev/null || echo "Linux")
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

    # ASCII Art and Message Display
    printf "%s\n" "${C_BOLD}${C_YELLOW}|￣￣￣￣￣￣￣￣￣￣￣|${C_RESET}"
    printf "%s\n" "$WRAPPED_MESSAGE" | while IFS= read -r line; do
        printf "${C_BOLD}${C_YELLOW}< ${C_CYAN}%-${MESSAGE_WIDTH}s${C_YELLOW} >${C_RESET}\n" "$line"
    done
    printf "%s\n" "${C_BOLD}${C_YELLOW}|＿＿＿＿＿＿＿＿＿＿＿|${C_RESET}"
    printf "%s\n" "   (\__/)  ||"
    printf "%s\n" "   (•ㅅ•)  ||"
    printf "%s\n" "   /  　  づ"

    printf "%s\n" "   ${C_BOLD}${C_YELLOW}dMMMMb  dMMMMMP dMP dMP${C_MAGENTA} .dMMMb   dMMMMMP dMMMMb  dMP dMP dMMMMMP dMMMMb ${C_RESET}  "
    printf "%s\n" "   ${C_BOLD}${C_YELLOW}dMP VMP dMP     dMP dMP${C_MAGENTA} dMP\" VP dMP     dMP.dMP dMP dMP dMP     dMP.dMP ${C_RESET}  "
    printf "%s\n" "  ${C_BOLD}${C_YELLOW}dMP dMP dMMMP   dMP dMP${C_MAGENTA}  VMMMb  dMMMP   dMMMMK\" dMP dMP dMMMP   dMMMMK\" ${C_RESET}"
    printf "%s\n" " ${C_BOLD}${C_YELLOW}dMP.aMP dMP      YMvAP\"${C_MAGENTA} dP .dMP dMP     dMP\"AMF  YMvAP\" dMP     dMP\"AMF ${C_RESET}"
    printf "%s\n" "${C_BOLD}${C_YELLOW}dMMMMP\" dMMMMMP    VP\"${C_MAGENTA}   VMMMP\" dMMMMMP dMP dMP    VP\"  dMMMMMP dMP dMP ${C_RESET}"

    # System Info Display
    echo
    printf "${C_GREEN}${C_BOLD}%-8s${C_RESET}: %s\n" "OS" "${OS_INFO}"
    printf "${C_GREEN}${C_BOLD}%-8s${C_RESET}: %s\n" "Kernel" "${KERNEL}"
    printf "${C_GREEN}${C_BOLD}%-8s${C_RESET}: %s\n" "CPU" "${CPU_INFO} (${CPU_CORES} cores)"
    printf "${C_GREEN}${C_BOLD}%-8s${C_RESET}: %s\n" "Memory" "${MEM_INFO}"
    printf "${C_GREEN}${C_BOLD}%-8s${C_RESET}: %s\n" "Disk" "${DISK_INFO}"
    printf "${C_GREEN}${C_BOLD}%-8s${C_RESET}: %s\n" "Uptime" "${UPTIME}"
    echo
}

COMMAND_TO_EXECUTE="${SSH_ORIGINAL_COMMAND}"
DISPLAY_BANNER=${DISPLAY_BANNER:-true}
case $SSH_ORIGINAL_COMMAND in
    "" | "bash" | "sh" | "zsh")
        # Only display banner if we think it's a login shell
        if [ "${DISPLAY_BANNER}" = "true" ]; then
            display_devserver_banner
        fi
        ;;
    *)
        ;;
esac

if [ -z "${SSH_ORIGINAL_COMMAND}" ]; then
    # If no command is provided, default to user login shell
    USER_SHELL=$(getent passwd dev | cut -d: -f7)
    COMMAND_TO_EXECUTE="${USER_SHELL:--/bin/sh}"
fi

#execute the command
eval "${COMMAND_TO_EXECUTE}"