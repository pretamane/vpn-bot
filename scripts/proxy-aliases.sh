#!/bin/bash
# sing-box proxy helper aliases and functions
# Source this in your ~/.bashrc or ~/.zshrc:
# echo "source ~/.config/sing-box/proxy-aliases.sh" >> ~/.bashrc

# Proxy environment variables
proxy_on() {
    export http_proxy=http://127.0.0.1:7897
    export https_proxy=$http_proxy
    export all_proxy=socks5h://127.0.0.1:7897
    echo "✓ Proxy enabled (127.0.0.1:7897)"
}

proxy_off() {
    unset http_proxy
    unset https_proxy
    unset all_proxy
    echo "✓ Proxy disabled"
}

proxy_status() {
    if [ -n "$http_proxy" ]; then
        echo "✓ Proxy is ON: $http_proxy"
    else
        echo "✗ Proxy is OFF"
    fi
    
    # Check sing-box status
    if systemctl --user is-active --quiet sing-box; then
        echo "✓ sing-box service: running"
    else
        echo "✗ sing-box service: not running"
    fi
}

proxy_test() {
    echo "Testing proxy connection..."
    local ip=$(curl -sS --proxy http://127.0.0.1:7897 https://api.ipify.org)
    if [ $? -eq 0 ]; then
        echo "✓ Proxy working! External IP: $ip"
    else
        echo "✗ Proxy test failed"
    fi
}

# Shorter aliases
alias pon='proxy_on'
alias poff='proxy_off'
alias pst='proxy_status'
alias ptest='proxy_test'

# proxychains shortcut
alias pc='proxychains4 -f ~/.proxychains/proxychains.conf'

# sing-box service shortcuts
alias sbstart='systemctl --user start sing-box'
alias sbstop='systemctl --user stop sing-box'
alias sbrestart='systemctl --user restart sing-box'
alias sbstatus='systemctl --user status sing-box'
alias sblogs='journalctl --user -u sing-box -f'
