import Cocoa

let maxSpriteWidth = 48, maxSpriteHeight = 20
let minInk = 60

struct Pet {
    let id: String
    let name: String
    let palette: [Character: NSColor]
    let sleep: [[String]]
    let awake: [[String]]
    let walk: [[String]]
    let w: Int, h: Int
    let halo: NSColor
    let dream: [String]
    let dreamColor: NSColor
    let thinking: String
    let keySaved: String
    let prompt: String
    var scale: CGFloat = 1
    var energy: Double = defaultEnergy
}

let defaultEnergy = 0.2

func hexColor(_ v: Any?) -> NSColor? {
    guard let s = v as? String, s.count == 7, s.hasPrefix("#"),
          let n = UInt32(s.dropFirst(), radix: 16) else { return nil }
    return NSColor(srgbRed: CGFloat((n >> 16) & 255) / 255, green: CGFloat((n >> 8) & 255) / 255,
                   blue: CGFloat(n & 255) / 255, alpha: 1)
}

func luminance(_ c: NSColor) -> CGFloat {
    let c = c.usingColorSpace(.sRGB) ?? c
    return 0.299 * c.redComponent + 0.587 * c.greenComponent + 0.114 * c.blueComponent
}

func fullPx(_ pet: Pet) -> CGFloat {
    max(1, min(3, (80 * pet.scale / CGFloat(pet.w) * 2).rounded(.down) / 2))
}

func buildPet(id: String, name: String, sprite raw: [String: Any], dream: String, dreamColor: NSColor,
              thinking: String, keySaved: String, prompt: String, scale: CGFloat = 1,
              energy: Double = defaultEnergy) -> Pet? {
    var pal: [Character: NSColor] = [:]
    for (k, v) in raw["palette"] as? [String: Any] ?? [:] where k.count == 1 && k != "." {
        if let c = hexColor(v) { pal[Character(k)] = c }
    }
    guard pal.count >= 2 else { return nil }

    func grid(_ v: Any?) -> [String]? {
        guard let rows = v as? [Any], !rows.isEmpty else { return nil }
        var g = rows.prefix(maxSpriteHeight).map { r -> String in
            String(String(describing: r).prefix(maxSpriteWidth).map { pal[$0] != nil ? $0 : "." })
        }
        while let last = g.last, !last.contains(where: { $0 != "." }) { g.removeLast() }
        while let first = g.first, !first.contains(where: { $0 != "." }) { g.removeFirst() }
        return g.isEmpty ? nil : g
    }
    func ink(_ g: [String]) -> Int { g.reduce(0) { $0 + $1.filter { $0 != "." }.count } }

    guard let asleep = grid(raw["asleep"]), ink(asleep) >= minInk else { return nil }
    var frames: [String: [String]] = ["asleep": asleep]
    for k in ["breathe", "awake", "awake2"] {
        if let f = grid(raw[k]), Double(ink(f)) >= Double(ink(asleep)) * 0.6, abs(f.count - asleep.count) <= 2 {
            frames[k] = f
        }
    }
    frames["breathe"] = frames["breathe"] ?? asleep
    frames["awake"] = frames["awake"] ?? asleep
    frames["awake2"] = frames["awake2"] ?? frames["awake"]!
    var walk = ["walk1", "walk2"].compactMap { grid(raw[$0]) }
        .filter { Double(ink($0)) >= Double(ink(asleep)) * 0.4 }
    if walk.count == 1 { walk.append(walk[0]) }
    for (i, f) in walk.enumerated() { frames["walk\(i + 1)"] = f }

    let height = frames.values.map { $0.count }.max()!
    let width = frames.values.flatMap { $0 }.map { $0.count }.max()!
    for (k, f) in frames {
        let fw = f.map { $0.count }.max()!
        frames[k] = Array(repeating: String(repeating: ".", count: width), count: height - f.count)
            + f.map { r in k.hasPrefix("walk")
                ? String(repeating: ".", count: width - fw) + r.padding(toLength: fw, withPad: ".", startingAt: 0)
                : r.padding(toLength: width, withPad: ".", startingAt: 0) }
    }

    var x0 = width, x1 = -1, y0 = height, y1 = -1
    for f in frames.values {
        for (y, r) in f.enumerated() {
            for (x, c) in r.enumerated() where c != "." {
                x0 = min(x0, x); x1 = max(x1, x); y0 = min(y0, y); y1 = max(y1, y)
            }
        }
    }
    for (k, f) in frames { frames[k] = f[y0...y1].map { String(Array($0)[x0...x1]) } }

    let filled = frames["asleep"]!.flatMap { Array($0) }.compactMap { pal[$0] }
    let dark = filled.map(luminance).reduce(0, +) / CGFloat(max(1, filled.count)) < 0.45
    let awake = frames["awake2"]! == frames["awake"]! ? [frames["awake"]!] : [frames["awake"]!, frames["awake2"]!]
    return Pet(id: id, name: name, palette: pal, sleep: [frames["asleep"]!, frames["breathe"]!],
               awake: awake, walk: ["walk1", "walk2"].compactMap { frames[$0] },
               w: x1 - x0 + 1, h: y1 - y0 + 1,
               halo: dark ? NSColor(white: 1, alpha: 0.35) : NSColor(white: 0, alpha: 0.28),
               dream: glyphs.dreams[dream] ?? glyphs.dreams["z"] ?? [], dreamColor: dreamColor,
               thinking: thinking, keySaved: keySaved, prompt: prompt, scale: scale, energy: energy)
}
