import Cocoa

typealias SavedPet = [String: Any]

let builtinPetData: [[String: Any]] = SharedData.json("pets")["pets"] as? [[String: Any]] ?? []

let builtinPets: [Pet] = builtinPetData.compactMap { p -> Pet? in
    guard let id = p["id"] as? String, let name = p["name"] as? String,
          let sprite = p["sprite"] as? [String: Any] else { return nil }
    return buildPet(id: id, name: name, sprite: sprite, dream: p["dream"] as? String ?? "z",
                    dreamColor: hexColor(p["dream_color"]) ?? .gray,
                    thinking: p["thinking"] as? String ?? "…hmm…", keySaved: p["saved"] as? String ?? "key saved. ask.",
                    prompt: petPrompt(name: name, description: p["description"] as? String ?? "a pet",
                                      personality: p["personality"] as? String ?? "",
                                      flavor: p["flavor"] as? [String] ?? []),
                    energy: p["zoomies"] as? Double ?? defaultEnergy)
}

let builtinIds = Set(builtinPets.map { $0.id })

var defaultPet: Pet { builtinPets[0] }

func makePet(id: String, saved: SavedPet) -> Pet? {
    guard let name = saved["name"] as? String else { return nil }
    let sprite: [String: Any], description: String, animal: String, preset: Personality?
    var scale: CGFloat = 1
    if saved["kind"] as? String == "breed" {
        let t = breedTemplate(saved["breed"] as? String)
        sprite = paintBreed(t.id, saved["color"] as? String)
        let colorName = (t.color(saved["color"] as? String)?.name ?? "").lowercased()
        description = "a little \(t.noun) (\(colorName))"
        animal = t.animal
        preset = personality(saved["personality"] as? String) ?? personality(t.defaultPersonality)
        scale = CGFloat(t.size ?? 1)
    } else {
        guard let s = saved["sprite"] as? [String: Any] else { return nil }
        sprite = s
        description = saved["description"] as? String ?? "a pet"
        animal = matches(description, #"\b(cat|kitten|kitty)\b"#) ? "cat" : "dog"
        preset = personality(saved["preset"] as? String)
    }
    if let p = preset {
        return buildPet(id: id, name: name, sprite: sprite, dream: p.dream[animal] ?? "z",
                        dreamColor: hexColor(p.dreamColor) ?? .gray, thinking: p.thinking, keySaved: p.saved,
                        prompt: petPrompt(name: name, description: description, personality: p.text, flavor: p.flavor),
                        scale: scale, energy: p.zoomies ?? defaultEnergy)
    }
    return buildPet(id: id, name: name, sprite: sprite, dream: saved["dream"] as? String ?? "z",
                    dreamColor: hexColor(saved["dream_color"]) ?? .gray,
                    thinking: "…hmm…", keySaved: "key saved. ask.",
                    prompt: petPrompt(name: name, description: description,
                                      personality: saved["personality"] as? String ?? "",
                                      flavor: saved["flavor"] as? [String] ?? []))
}

func petFlavor(_ saved: SavedPet) -> String {
    let id = (saved["kind"] as? String == "breed" ? saved["personality"] : saved["preset"]) as? String
    return (personality(id)?.flavor ?? saved["flavor"] as? [String])?.last ?? "hi."
}

func loadSavedPets() -> [String: SavedPet] {
    guard let data = FileManager.default.contents(atPath: Paths.pets),
          let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return [:] }
    return json["pets"] as? [String: SavedPet] ?? [:]
}

func writeSavedPets(_ pets: [String: SavedPet]) {
    if let data = try? JSONSerialization.data(withJSONObject: ["pets": pets], options: [.prettyPrinted]) {
        FileManager.default.createFile(atPath: Paths.pets, contents: data)
    }
}

func newPetId(for name: String) -> String {
    let base = String(name.lowercased().unicodeScalars
        .filter { CharacterSet.alphanumerics.contains($0) && $0.isASCII }.map(Character.init))
    var id = base.isEmpty ? "pet" : base, n = 2
    let taken = builtinIds.union(loadSavedPets().keys).union(["pet"])
    while taken.contains(id) { id = "\(base)\(n)"; n += 1 }
    return id
}

func allPets() -> [Pet] {
    let cfg = loadConfig()
    let saved = loadSavedPets().sorted { $0.key < $1.key }.compactMap { makePet(id: $0.key, saved: $0.value) }
    return (builtinPets + saved).map { wearHat($0, hatFor($0.id, cfg)) }
}

func awakePet() -> Pet {
    let id = UserDefaults.standard.string(forKey: "dog") ?? defaultPet.id
    return allPets().first { $0.id == id } ?? defaultPet
}

let photoMaxSide: CGFloat = 768

var photoExampleSprite: [String: Any] {
    (builtinPetData.first { $0["id"] as? String == "stewart" } ?? builtinPetData.last)?["sprite"] as? [String: Any] ?? [:]
}

func cleanPhotoPet(_ d: [String: Any], name: String) -> SavedPet? {
    guard let sprite = d["sprite"] as? [String: Any],
          buildPet(id: "check", name: name, sprite: sprite, dream: "z", dreamColor: .gray,
                   thinking: "", keySaved: "", prompt: "") != nil else { return nil }
    let flavor = (d["flavor"] as? [Any] ?? []).compactMap { f -> String? in
        let w = String(describing: f).split(separator: " ").prefix(2).joined(separator: " ")
        return w.isEmpty ? nil : w
    }
    let dream = (d["dream"] as? String).flatMap { glyphs.dreams[$0] != nil ? $0 : nil } ?? "z"
    return ["name": name, "sprite": sprite,
            "description": String((d["description"] as? String ?? "a pet").prefix(80)),
            "personality": String((d["personality"] as? String ?? "Friendly and curious.").prefix(240)),
            "flavor": Array((flavor + ["hmm.", "ok.", "yay."]).prefix(3)), "dream": dream,
            "dream_color": (d["dream_color"] as? String).flatMap { hexColor($0) != nil ? $0 : nil } ?? "#c8a070"]
}

func jpegData(_ img: NSImage, maxSide: CGFloat) -> Data? {
    guard let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { return nil }
    let w = CGFloat(cg.width), h = CGFloat(cg.height), s = min(1, maxSide / max(w, h))
    let nw = max(1, Int(w * s)), nh = max(1, Int(h * s))
    guard let ctx = CGContext(data: nil, width: nw, height: nh, bitsPerComponent: 8, bytesPerRow: 0,
                              space: CGColorSpaceCreateDeviceRGB(),
                              bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue) else { return nil }
    ctx.interpolationQuality = .high
    ctx.draw(cg, in: CGRect(x: 0, y: 0, width: nw, height: nh))
    guard let out = ctx.makeImage() else { return nil }
    return NSBitmapImageRep(cgImage: out).representation(using: .jpeg, properties: [.compressionFactor: 0.85])
}
