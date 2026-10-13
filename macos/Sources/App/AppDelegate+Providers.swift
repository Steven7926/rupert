import Cocoa

extension AppDelegate {
    func connectAsync() {
        say("…connecting to \(currentProvider().label)…")
        connectProvider { [weak self] msg in self?.say(msg) }
    }

    @objc func chooseProvider(_ sender: NSMenuItem) {
        guard let id = sender.representedObject as? String else { return }
        setConfig("provider", id)
        var p = currentProvider()
        if id == "custom" && p.base.isEmpty {
            guard askForURL(connect: false) else { return }
            p = currentProvider()
        }
        if p.needsKey && p.key.isEmpty {
            guard askForKey(connect: false) else { say("\(p.label) needs a key. paste it here ⏎"); return }
        }
        connectAsync()
    }

    @objc func setKeyMenu() { _ = askForKey(connect: true) }
    @objc func setURLMenu() { _ = askForURL(connect: true) }

    func askForKey(connect: Bool) -> Bool {
        let p = currentProvider()
        guard let key = textPrompt(title: "API key", message: "\(p.label) API key:", secure: true) else { return false }
        setConfig("keys", p.id, key)
        if connect { connectAsync() }
        return true
    }

    func askForURL(connect: Bool) -> Bool {
        let p = currentProvider()
        guard var url = textPrompt(title: "Server URL", message: "OpenAI-compatible base URL (ends in /v1):",
                                   value: p.base.isEmpty ? "http://localhost:8000/v1" : p.base) else { return false }
        while url.hasSuffix("/") { url.removeLast() }
        setConfig("base_urls", p.id, url)
        if connect { connectAsync() }
        return true
    }

    @objc func chooseModel(_ sender: NSMenuItem) {
        let vision = sender.tag == 1
        let p = currentProvider()
        listModels(p) { ids in
            DispatchQueue.main.async {
                NSApp.activate(ignoringOtherApps: true)
                let current = vision ? p.vision : p.model
                let alert = NSAlert()
                alert.messageText = "Choose model"
                alert.informativeText = vision ? "Model for reading pet photos (must accept images):"
                                               : "Model for answers (small and fast is best):"
                let box = NSComboBox(frame: NSRect(x: 0, y: 0, width: 320, height: 26))
                box.addItems(withObjectValues: ids.isEmpty ? [current] : ids)
                box.numberOfVisibleItems = 14
                box.completes = true
                box.stringValue = current
                alert.accessoryView = box
                alert.addButton(withTitle: "Use Model")
                alert.addButton(withTitle: "Cancel")
                guard alert.runModal() == .alertFirstButtonReturn else { return }
                let pick = box.stringValue.trimmingCharacters(in: .whitespaces)
                guard !pick.isEmpty else { return }
                setConfig(vision ? "vision_models" : "models", p.id, pick)
                self.say("\(vision ? "photo model" : "model"): \(pick)")
            }
        }
    }

    func textPrompt(title: String, message: String, value: String = "", secure: Bool = false,
                    button: String = "OK") -> String? {
        NSApp.activate(ignoringOtherApps: true)
        let alert = NSAlert()
        alert.messageText = title
        alert.informativeText = message
        let frame = NSRect(x: 0, y: 0, width: 300, height: 24)
        let field: NSTextField = secure ? NSSecureTextField(frame: frame) : NSTextField(frame: frame)
        field.stringValue = value
        alert.accessoryView = field
        alert.addButton(withTitle: button)
        alert.addButton(withTitle: "Cancel")
        alert.window.initialFirstResponder = field
        guard alert.runModal() == .alertFirstButtonReturn else { return nil }
        let v = field.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        return v.isEmpty ? nil : v
    }
}
