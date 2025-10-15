# /etc/profile

# Set a default prompt
PS1='\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '

# Alias definitions.
alias ls='ls --color=auto'
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

# Add /usr/local/bin to path if it exists
if [ -d "/usr/local/bin" ] ; then
    PATH="/usr/local/bin:$PATH"
fi

# Add sbin paths for root
if [ "$(id -u)" = "0" ]; then
    PATH="/usr/local/sbin:/usr/sbin:/sbin:$PATH"
fi
