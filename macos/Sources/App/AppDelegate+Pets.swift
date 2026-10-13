import Cocoa

extension AppDelegate {
    @objc func pickPet(_ sender: NSMenuItem) {
        if let id = sender.representedObject as? String, let p = allPets().first(where: { $0.id == id }) {
            switchTo(p)
        }
    }

    @objc func removePet() {
        var pets = loadSavedPets()
        pets.removeValue(forKey: pet.id)
        writeSavedPets(pets)
        switchTo(defaultPet)
    }

    @objc func newPet() { showPetForm(editing: nil) }
    @objc func editPet() { showPetForm(editing: pet.id) }

    private func save(_ saved: SavedPet, as id: String) {
        var pets = loadSavedPets()
        pets[id] = saved
        writeSavedPets(pets)
        if let p = allPets().first(where: { $0.id == id }) ?? makePet(id: id, saved: saved) { switchTo(p) }
        say("\(saved["name"] as? String ?? "") here! \(petFlavor(saved))\nterminal: pet \(id) on")
    }

    private func showPetForm(editing editId: String?) {
        NSApp.activate(ignoringOtherApps: true)
        let existing = editId.flatMap { loadSavedPets()[$0] }
        let form = PetForm(existing: existing)
        let alert = NSAlert()
        alert.messageText = existing == nil ? "New pet" : "Edit \(existing?["name"] as? String ?? "pet")"
        alert.informativeText = "Upload a photo and the AI draws your pet, or pick a breed and color."
        alert.addButton(withTitle: existing == nil ? "Add Pet" : "Save")
        alert.addButton(withTitle: "Cancel")
        alert.accessoryView = form.view
        form.okButton = alert.buttons[0]
        form.refresh()
        alert.window.initialFirstResponder = form.name
        guard alert.runModal() == .alertFirstButtonReturn else { return }

        let choice = form.choice
        let id = editId ?? newPetId(for: choice.name)
        if !choice.fromPhoto {
            save(["name": choice.name, "kind": "breed", "breed": choice.breed, "color": choice.color,
                  "personality": choice.personality], as: id)
            return
        }
        guard let url = choice.photoURL else {
            guard var saved = existing else { return }
            saved["name"] = choice.name
            saved["preset"] = choice.personality
            saved.removeValue(forKey: "kind")
            save(saved, as: id)
            return
        }
        drawFromPhoto(url, name: choice.name, preset: choice.personality, id: id)
    }

    private func drawFromPhoto(_ url: URL, name: String, preset: String, id: String) {
        let prov = currentProvider()
        guard prov.ready else { say("set up an AI provider first. right-click → AI provider."); return }
        guard let img = NSImage(contentsOf: url), let jpeg = jpegData(img, maxSide: photoMaxSide) else {
            say("can't read that photo."); return
        }
        say("…drawing \(name)… (takes ~30s)")
        let prompt = drawPetPrompt(name: name, example: photoExampleSprite)
        let budget = prov.api == "anthropic" ? 6000 : 10000
        chat(prov, system: nil, messages: [["role": "user", "content": prompt]], maxTokens: budget,
             model: prov.vision, imageB64: jpeg.base64EncodedString(), timeout: 180) { r in
            var saved: SavedPet?
            var problem = "grr. couldn't draw that one. try again or another photo."
            switch r {
            case .failure(let e):
                problem = friendlyError(e)
                if case .http(let c, _) = e, c != 401, c != 403 { problem += " (photo model must accept images)" }
            case .success(let text):
                if let a = text.firstIndex(of: "{"), let b = text.lastIndex(of: "}"), a < b,
                   let obj = try? JSONSerialization.jsonObject(with: Data(text[a...b].utf8)) as? [String: Any] {
                    if let e = obj["error"] as? String { problem = e } else { saved = cleanPhotoPet(obj, name: name) }
                }
            }
            DispatchQueue.main.async {
                guard var saved else { self.say(problem); return }
                if !preset.isEmpty { saved["preset"] = preset }
                self.save(saved, as: id)
            }
        }
    }
}
