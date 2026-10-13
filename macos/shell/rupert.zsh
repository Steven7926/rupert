_rupert_dog() {
  case "$2" in
    on|"")
      pkill -x Rupert; sleep 0.3
      defaults write local.rupert dog "$1"
      open "$_RUPERT_APP" ;;
    off)
      pkill -x Rupert && echo "$1 sleeps. bye." || echo "$1 already off." ;;
    restart)
      _rupert_dog "$1" on ;;
    *)
      echo "usage: $1 [on|off|restart]" ;;
  esac
}
rupert()  { _rupert_dog rupert  "$1"; }
stewart() { _rupert_dog stewart "$1"; }
pet()     { [ -n "$1" ] && _rupert_dog "${1:l}" "$2" || echo "usage: pet <name> [on|off|restart]"; }

_rupert_pet_command() {
  (( $# >= 1 && $# <= 2 )) || return 1
  _rupert_name=${1:l}
  case "$_rupert_name" in ""|*[!a-z0-9]*) return 1 ;; esac
  "$_RUPERT_APP/Contents/MacOS/Rupert" --is-pet "$_rupert_name" 2>/dev/null
}

if [[ -z $_RUPERT_CNF ]]; then
  _RUPERT_CNF=1
  (( $+functions[command_not_found_handler] )) && functions[_rupert_prev_cnf]=$functions[command_not_found_handler]
  command_not_found_handler() {
    if _rupert_pet_command "$@"; then _rupert_dog "$_rupert_name" "$2"; return; fi
    if (( $+functions[_rupert_prev_cnf] )); then _rupert_prev_cnf "$@"; return; fi
    print -u2 "zsh: command not found: $1"
    return 127
  }
fi
