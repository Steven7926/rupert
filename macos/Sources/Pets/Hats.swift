import Cocoa

struct Hat: Decodable {
    let id: String
    let name: String
    let palette: [String: String]
    let rows: [String]
}

private struct HatsFile: Decodable { let hats: [Hat] }

let hats = SharedData.decode(HatsFile.self, from: "hats").hats

func headAnchor(_ frame: [String]) -> (Int, Double) {
    let width = frame.map { $0.count }.max() ?? 0
    let cut = Int(Double(width) * 0.55)
    for (y, r) in frame.enumerated() {
        let xs = Array(r).enumerated().filter { $0.offset >= cut && $0.element != "." }.map { $0.offset }
        if let a = xs.min(), let b = xs.max() { return (y, Double(a + b) / 2) }
    }
    return (0, Double(width) * 0.8)
}

func applyHat(_ frames: [[String]], rows: [String]) -> [[String]] {
    let hh = rows.count, hw = rows.map { $0.count }.max() ?? 0
    let anchors = frames.map(headAnchor)
    let pad = max(0, anchors.map { hh - 1 - $0.0 }.max() ?? 0)
    return zip(frames, anchors).map { f, a in
        let width = f.map { $0.count }.max() ?? 0
        var g = Array(repeating: Array(repeating: Character("."), count: width), count: pad)
            + f.map { Array($0.padding(toLength: width, withPad: ".", startingAt: 0)) }
        let top = a.0 + pad - (hh - 1)
        let left = Int((a.1 - Double(hw - 1) / 2).rounded())
        for (dy, hatRow) in rows.enumerated() {
            for (dx, ch) in hatRow.enumerated() where ch != "." {
                let x = left + dx, y = top + dy
                if x >= 0 && x < width && y >= 0 && y < g.count { g[y][x] = ch }
            }
        }
        return g.map { String($0) }
    }
}

func hatFor(_ petId: String, _ cfg: Config? = nil) -> String {
    let h = ((cfg ?? loadConfig())["hats"] as? [String: String])?[petId] ?? ""
    return hats.contains { $0.id == h } ? h : ""
}

func wearHat(_ pet: Pet, _ hatId: String) -> Pet {
    guard let hat = hats.first(where: { $0.id == hatId }) else { return pet }
    let dressed = applyHat(pet.sleep + pet.awake + pet.walk, rows: hat.rows)
    let n1 = pet.sleep.count, n2 = pet.sleep.count + pet.awake.count
    var pal = pet.palette
    for (k, v) in hat.palette { if let ch = k.first, let c = hexColor(v) { pal[ch] = c } }
    return Pet(id: pet.id, name: pet.name, palette: pal, sleep: Array(dressed[..<n1]),
               awake: Array(dressed[n1..<n2]), walk: Array(dressed[n2...]),
               w: pet.w, h: dressed.first?.count ?? pet.h, halo: pet.halo, dream: pet.dream,
               dreamColor: pet.dreamColor, thinking: pet.thinking, keySaved: pet.keySaved, prompt: pet.prompt,
               scale: pet.scale, energy: pet.energy)
}
