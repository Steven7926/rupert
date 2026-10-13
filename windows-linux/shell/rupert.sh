_rupert() { PYTHONPATH="$_RUPERT_DIR" "$_RUPERT_DIR/venv/bin/python" -m rupert "$@"; }
rupert()  { _rupert rupert  "$@"; }
stewart() { _rupert stewart "$@"; }
pet()     { _rupert "$@"; }

_rupert_pet_command() {
  [ $# -ge 1 ] && [ $# -le 2 ] || return 1
  _rupert_name=$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')
  case "$_rupert_name" in ""|*[!a-z0-9]*) return 1 ;; esac
  _rupert --is-pet "$_rupert_name"
}

if [ -z "$_RUPERT_CNF" ]; then
  _RUPERT_CNF=1
  if [ -n "$ZSH_VERSION" ]; then
    eval '(( $+functions[command_not_found_handler] )) && functions[_rupert_prev_cnf]=$functions[command_not_found_handler]'
    command_not_found_handler() {
      if _rupert_pet_command "$@"; then _rupert "$_rupert_name" "${2:-on}"; return; fi
      if typeset -f _rupert_prev_cnf >/dev/null; then _rupert_prev_cnf "$@"; return; fi
      printf 'zsh: command not found: %s\n' "$1" >&2
      return 127
    }
  elif [ -n "$BASH_VERSION" ]; then
    if declare -F command_not_found_handle >/dev/null; then
      eval "$(declare -f command_not_found_handle | sed '1s/command_not_found_handle/_rupert_prev_cnf/')"
    fi
    command_not_found_handle() {
      if _rupert_pet_command "$@"; then _rupert "$_rupert_name" "${2:-on}"; return; fi
      if declare -F _rupert_prev_cnf >/dev/null; then _rupert_prev_cnf "$@"; return; fi
      printf 'bash: %s: command not found\n' "$1" >&2
      return 127
    }
  fi
fi
