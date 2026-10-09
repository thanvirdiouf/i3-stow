#
# ~/.bashrc
#

# Non-interactive shells: bail out
[[ $- != *i* ]] && return

# History
HISTCONTROL=ignoreboth
HISTSIZE=10000
HISTFILESIZE=20000
shopt -s histappend
shopt -s checkwinsize
# Lightweight cross-terminal history sharing
PROMPT_COMMAND="history -a; history -n${PROMPT_COMMAND:+; $PROMPT_COMMAND}"

# Aliases
alias grep='grep --color=auto'
command -v eza >/dev/null 2>&1 && alias ls='eza'

# Prompt — pick ONE
if command -v starship >/dev/null 2>&1; then
  eval "$(starship init bash)"
else
  PS1="\[\e[32m\]\u@\h \[\e[34m\]\w \$ \[\e[0m\]"
fi

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"                   # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion" # This loads nvm bash_completion

export PATH="$HOME/.local/opt/ast-grep:$PATH"
. "$HOME/.cargo/env"

alias uud="sudo apt update"
alias uug="sudo apt upgrade"
