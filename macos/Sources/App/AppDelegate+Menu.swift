import Cocoa

extension AppDelegate {
    func showMenu(_ event: NSEvent) {
        let menu = NSMenu()
        menu.autoenablesItems = false
        let talk = menu.addItem(withTitle: hotkeyNote.isEmpty ? "Talk to \(pet.name)" : "Talk to \(pet.name) (\(hotkeyNote))",
                                action: #selector(hotkeyPressed), keyEquivalent: hotkeyNote.isEmpty ? "r" : "")
        talk.keyEquivalentModifierMask = [.control, .option]
        talk.target = self
        menu.addItem(.separator())
        let copyItem = item(in: menu, "Copy command", #selector(copyAnswer))
        copyItem.isEnabled = lastReply.flatMap(commandPart) != nil
        item(in: menu, "Clear chat", #selector(clearChat))
        menu.addItem(.separator())
        submenu(in: menu, "Pets", petsMenu())
        menu.addItem(.separator())
        submenu(in: menu, "AI provider · \(currentProvider().label)", providerMenu())
        let accessories = NSMenu()
        submenu(in: accessories, "Hat", hatMenu())
        submenu(in: menu, "Accessories", accessories)
        let activity = choices(activitySettings.modes.map { ($0.id, $0.label) },
                               current: activityMode(loadConfig()), action: #selector(setActivity(_:)))
        activity.addItem(.separator())
        item(in: activity, "Glide between windows", #selector(toggleGlide)).state = glideBetweenWindows ? .on : .off
        submenu(in: menu, "Activity", activity)
        submenu(in: menu, "Appearance", choices([("auto", "Auto (match system)"), ("light", "Light"), ("dark", "Dark")],
                                                current: loadConfig()["appearance"] as? String ?? "auto",
                                                action: #selector(setAppearance(_:))))
        menu.addItem(.separator())
        menu.addItem(withTitle: "Quit \(pet.name)", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "")
        NSMenu.popUpContextMenu(menu, with: event, for: petView)
    }

    private func petsMenu() -> NSMenu {
        let menu = choices(allPets().map { ($0.id, $0.name) }, current: pet.id, action: #selector(pickPet(_:)))
        menu.addItem(.separator())
        item(in: menu, "Add new pet…", #selector(newPet))
        if !builtinIds.contains(pet.id) {
            item(in: menu, "Edit \(pet.name)…", #selector(editPet))
            item(in: menu, "Remove \(pet.name)", #selector(removePet))
        }
        return menu
    }

    private func providerMenu() -> NSMenu {
        let p = currentProvider()
        let menu = choices(providerPresets.map { ($0.id, $0.label) }, current: p.id, action: #selector(chooseProvider(_:)))
        menu.addItem(.separator())
        item(in: menu, "Model: \(p.model.isEmpty ? "(none)" : p.model)…", #selector(chooseModel(_:)))
        item(in: menu, "Photo model: \(p.vision.isEmpty ? "(none)" : p.vision)…", #selector(chooseModel(_:))).tag = 1
        if p.needsKey || p.id == "custom" { item(in: menu, "Set API key…", #selector(setKeyMenu)) }
        if localServers.contains(p.id) {
            item(in: menu, "Server URL: \(p.base.isEmpty ? "(none)" : p.base)…", #selector(setURLMenu))
        }
        return menu
    }

    private func hatMenu() -> NSMenu {
        let options: [(String, String)] = [("", "No hat")] + hats.map { ($0.id, $0.name) }
        return choices(options, current: hatFor(pet.id), action: #selector(setHat(_:)))
    }

    private func choices(_ options: [(String, String)], current: String, action: Selector) -> NSMenu {
        let menu = NSMenu()
        menu.autoenablesItems = false
        for (id, label) in options {
            let it = item(in: menu, label, action)
            it.representedObject = id
            it.state = id == current ? .on : .off
        }
        return menu
    }

    @discardableResult
    private func item(in menu: NSMenu, _ title: String, _ action: Selector) -> NSMenuItem {
        let it = menu.addItem(withTitle: title, action: action, keyEquivalent: "")
        it.target = self
        return it
    }

    private func submenu(in menu: NSMenu, _ title: String, _ sub: NSMenu) {
        menu.setSubmenu(sub, for: menu.addItem(withTitle: title, action: nil, keyEquivalent: ""))
    }

    @objc func setHat(_ sender: NSMenuItem) {
        setConfig("hats", pet.id, sender.representedObject as? String ?? "")
        if let dressed = allPets().first(where: { $0.id == pet.id }) {
            pet = dressed
            petView.pet = dressed
            lastTarget = nil
            follow()
        }
        cheer(1.5)
    }

    @objc func setActivity(_ sender: NSMenuItem) {
        guard let mode = sender.representedObject as? String else { return }
        setConfig("activity", mode)
        nextWalk = Date().addingTimeInterval(3)
        if mode == "stay" && spot < 1 && !petView.compact && lastTarget != nil {
            walkTarget = 1; walkSpeed = 36; lapsLeft = 0
            petView.facing = 1
            petView.mode = "walk"
            replace()
        }
    }

    @objc func toggleGlide() {
        glideBetweenWindows.toggle()
        setConfig("glide", glideBetweenWindows)
        if !glideBetweenWindows { glideUntil = .distantPast }
    }

    @objc func setAppearance(_ sender: NSMenuItem) {
        setConfig("appearance", sender.representedObject as? String ?? "auto")
        bubble.applyTheme(themeName())
        resizeBubble()
    }

    func themeName() -> String {
        let pref = loadConfig()["appearance"] as? String ?? "auto"
        if themes[pref] != nil { return pref }
        return NSApp.effectiveAppearance.bestMatch(from: [.darkAqua, .aqua]) == .darkAqua ? "dark" : "light"
    }
}
