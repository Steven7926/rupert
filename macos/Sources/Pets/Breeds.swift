import Cocoa

struct ToneSpec: Decodable {
    let region: String, tone: String, k: Double
    init(from decoder: Decoder) throws {
        var c = try decoder.unkeyedContainer()
        region = try c.decode(String.self)
        tone = try c.decode(String.self)
        k = try c.decode(Double.self)
    }
}

struct BreedColor: Decodable {
    let id: String, name: String
    let regions: [String: String]
    init(from decoder: Decoder) throws {
        let all = try decoder.singleValueContainer().decode([String: String].self)
        id = all["id"] ?? ""
        name = all["name"] ?? id
        regions = all
    }
}

struct BreedTemplate: Decodable {
    let id: String, name: String, noun: String, animal: String
    let defaultPersonality: String
    let size: Double?
    let frames: [String: [String]]
    let fixed: [String: String]
    let tones: [String: ToneSpec]
    let colors: [BreedColor]
    enum CodingKeys: String, CodingKey {
        case id, name, noun, animal, size, frames, fixed, tones, colors
        case defaultPersonality = "default"
    }

    func color(_ id: String?) -> BreedColor? { colors.first { $0.id == id } ?? colors.first }
}

struct Personality: Decodable {
    let id: String, name: String
    let animal: String
    let text: String
    let flavor: [String]
    let thinking: String, saved: String
    let dream: [String: String]
    let dreamColor: String
    let zoomies: Double?
    enum CodingKeys: String, CodingKey {
        case id, name, text, flavor, thinking, saved, dream, zoomies
        case animal = "for", dreamColor = "dream_color"
    }
}

private struct BreedsFile: Decodable {
    let breeds: [BreedTemplate]
    let personalities: [Personality]
}

private let breedsFile = SharedData.decode(BreedsFile.self, from: "breeds")
let breedTemplates = breedsFile.breeds
let personalityPresets = breedsFile.personalities

func breedTemplate(_ id: String?) -> BreedTemplate {
    breedTemplates.first { $0.id == id } ?? breedTemplates[0]
}

func personality(_ id: String?) -> Personality? { personalityPresets.first { $0.id == id } }

func personalities(for animal: String) -> [Personality] {
    personalityPresets.filter { animal.isEmpty || $0.animal == "any" || $0.animal == animal }
}

func paintBreed(_ breedId: String?, _ colorId: String?) -> [String: Any] {
    let t = breedTemplate(breedId)
    let regions = t.color(colorId)?.regions ?? [:]
    var pal = t.fixed
    for (letter, spec) in t.tones {
        if let hex = regions[spec.region] { pal[letter] = rampColor(hex, spec.tone, spec.k) }
    }
    var sprite: [String: Any] = t.frames
    sprite["palette"] = pal
    return sprite
}

func rampColor(_ hex: String, _ tone: String, _ k: Double) -> String {
    guard let n = UInt32(hex.dropFirst(), radix: 16) else { return hex }
    var c = [Double((n >> 16) & 255), Double((n >> 8) & 255), Double(n & 255)]
    func mix(_ to: [Double], _ t: Double) { c = zip(c, to).map { $0 + ($1 - $0) * t } }
    if k < 1 { c = c.map { $0 * k } } else if k > 1 { mix([255, 255, 255], k - 1) }
    let lum = (0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]) / 255
    switch tone {
    case "hi": if lum < 0.2 { mix([150, 156, 190], 0.30) } else { mix([255, 246, 228], 0.32) }
    case "sh": c = [c[0] * 0.80, c[1] * 0.78, c[2] * 0.82]
    case "dp": c = [c[0] * 0.64, c[1] * 0.61, c[2] * 0.68]
    case "out": c = [c[0] * 0.42, c[1] * 0.38, c[2] * 0.42]
    default: break
    }
    let b = c.map { max(0, min(255, Int($0 + 0.5))) }
    return "#" + b.map { ($0 < 16 ? "0" : "") + String($0, radix: 16) }.joined()
}
