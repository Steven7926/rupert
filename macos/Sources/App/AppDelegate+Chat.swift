import Cocoa

extension AppDelegate {
    var askPrompt: String {
        let p = currentProvider()
        if p.ready { return "ask \(pet.id)…" }
        if p.needsKey && p.key.isEmpty {
            return p.id == "anthropic" ? "paste an API key ⏎ (any provider)" : "paste \(p.label) key ⏎"
        }
        return "right-click → AI provider to set up"
    }

    func toggleBubble() {
        if bubblePanel.isVisible { closeBubble(); return }
        petView.awakeMode = true
        if petView.mode == "walk" || petView.mode == "run" { petView.mode = "sleep"; lapsLeft = 0 }
        bubble.applyTheme(themeName())
        bubble.setPlaceholder(askPrompt)
        resizeBubble()
        bubblePanel.orderFrontRegardless()
        positionBubble()
        bubblePanel.makeKey()
        bubblePanel.makeFirstResponder(bubble.input)
        bubble.needsDisplay = true
    }

    func openBubble() { if !bubblePanel.isVisible { toggleBubble() } }

    func closeBubble() {
        bubblePanel.orderOut(nil)
        petView.awakeMode = false
    }

    func resizeBubble() {
        bubble.relayout()
        bubblePanel.setContentSize(bubble.frame.size)
        positionBubble()
    }

    func say(_ text: String) {
        openBubble()
        bubble.setAnswer(text)
        bubble.setPlaceholder(askPrompt)
        resizeBubble()
    }

    func windowDidResignKey(_ notification: Notification) {
        if (notification.object as? NSWindow) === bubblePanel { closeBubble() }
    }

    func control(_ control: NSControl, textView: NSTextView, doCommandBy sel: Selector) -> Bool {
        if sel == #selector(NSResponder.cancelOperation(_:)) { closeBubble(); return true }
        if sel == #selector(NSResponder.insertNewline(_:)),
           NSApp.currentEvent?.modifierFlags.intersection([.shift, .option]).isEmpty == false {
            textView.insertNewlineIgnoringFieldEditor(nil)
            return true
        }
        return false
    }

    func controlTextDidChange(_ obj: Notification) {
        guard (obj.object as? NSTextField) === bubble.input else { return }
        let before = bubble.frame.height
        bubble.relayout()
        if bubble.frame.height != before { resizeBubble() }
    }

    @objc func submit() {
        let text = bubble.input.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !busy else { return }
        bubble.input.stringValue = ""

        let prov = currentProvider()
        guard prov.ready else {
            if prov.needsKey && prov.key.isEmpty && looksLikeKey(text) {
                let id = providerForKey(text, current: prov.id)
                setConfig("provider", id)
                setConfig("keys", id, text)
                connectAsync()
            } else {
                say("not set up yet. right-click → AI provider.")
            }
            return
        }

        if matches(text, thanksPattern) { cheer(2.5) }
        busy = true
        bubble.setPlaceholder(text)
        bubble.setAnswer(pet.thinking)
        resizeBubble()
        history.append(["role": "user", "content": text])
        if history.count > 6 { history.removeFirst(history.count - 6) }

        let budget = prov.api == "anthropic" ? 60 : 400
        chat(prov, system: pet.prompt + timeNote(), messages: history, maxTokens: budget) { [weak self] r in
            var reply = "grr. no answer.", ok = false
            switch r {
            case .success(let text):
                let t = tighten(text)
                if !t.isEmpty { reply = t; ok = true }
            case .failure(let e):
                reply = friendlyError(e)
            }
            DispatchQueue.main.async { self?.finish(reply: reply, ok: ok) }
        }
    }

    func finish(reply: String, ok: Bool) {
        busy = false
        if ok {
            history.append(["role": "assistant", "content": reply])
            lastReply = reply
        } else if !history.isEmpty {
            history.removeLast()
        }
        let cmd = ok ? commandPart(reply) : nil
        if matches(cmd, destructivePattern) { petView.nervousUntil = Date().addingTimeInterval(2.5) }
        bubble.showCopied(false)
        bubble.copyButton.isHidden = cmd == nil
        bubble.setAnswer(reply, command: cmd)
        bubble.setPlaceholder(askPrompt)
        resizeBubble()
    }

    @objc func clearChat() {
        history.removeAll()
        lastReply = nil
        bubble.copyButton.isHidden = true
        bubble.setAnswer("")
        resizeBubble()
    }

    @objc func copyAnswer() {
        guard let reply = lastReply, let text = commandPart(reply) else { return }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(text, forType: .string)
        bubble.showCopied(true)
        cheer()
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.2) { [weak self] in self?.bubble.showCopied(false) }
    }

    func petted() {
        guard !["walk", "run", "carry"].contains(petView.mode) else { return }
        petView.happyUntil = Date().addingTimeInterval(2.5)
        nextWalk = max(nextWalk, Date().addingTimeInterval(30))
    }

    func cheer(_ seconds: TimeInterval = 1.8) { petView.happyUntil = Date().addingTimeInterval(seconds) }
}
