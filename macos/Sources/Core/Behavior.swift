import Cocoa

struct ActivityFile: Decodable {
    struct Mode: Decodable { let id: String, label: String }
    struct Slot: Decodable { let start: Int, end: Int, gap: [Double]?, speed: Double }
    struct Zoomies: Decodable {
        let speed: Double, laps: [Int], fastSlot: Double, slowSlot: Double
        let runLengths: [Double]
        enum CodingKeys: String, CodingKey {
            case speed, laps, fastSlot = "fast_slot", slowSlot = "slow_slot", runLengths = "run_lengths"
        }
    }
    let modes: [Mode]
    let schedule: [Slot]
    let zoomies: Zoomies
}

let activitySettings = SharedData.decode(ActivityFile.self, from: "activity")
let defaultWalkSpeed: CGFloat = 30

func activityMode(_ cfg: Config) -> String {
    let a = cfg["activity"] as? String ?? ""
    if activitySettings.modes.contains(where: { $0.id == a }) { return a }
    return (cfg["wander"] as? Bool ?? true) ? "normal" : "stay"
}

func walkPlan(_ mode: String) -> (Double?, CGFloat) {
    switch mode {
    case "stay": return (nil, defaultWalkSpeed)
    case "normal": return (Double.random(in: 60...240), defaultWalkSpeed)
    default:
        let hour = Calendar.current.component(.hour, from: Date())
        let h = hour >= 6 ? hour : hour + 24
        for slot in activitySettings.schedule where slot.start <= h && h < slot.end {
            let gap = slot.gap.flatMap { $0.count == 2 ? Double.random(in: $0[0]...$0[1]) : nil }
            return (gap, CGFloat(slot.speed))
        }
        return (Double.random(in: 60...240), defaultWalkSpeed)
    }
}

let zoomiesSpeed = CGFloat(activitySettings.zoomies.speed)

func zoomiesChance(mode: String, walkSpeed: CGFloat, energy: Double) -> Double {
    if mode == "stay" { return 0 }
    let z = activitySettings.zoomies
    let slot = mode == "time" ? (walkSpeed >= 40 ? z.fastSlot : z.slowSlot) : 1
    return max(0, min(0.9, energy * slot))
}

func zoomiesTarget(spot: CGFloat, direction: CGFloat) -> CGFloat {
    for d in [direction, -direction] {
        let length = CGFloat(activitySettings.zoomies.runLengths.randomElement() ?? 1)
        let target = max(0, min(1, spot + d * length))
        if abs(target - spot) >= 0.12 { return target }
    }
    return spot > 0.5 ? 0 : 1
}

func zoomiesLaps() -> Int {
    let laps = activitySettings.zoomies.laps
    return laps.count == 2 ? Int.random(in: laps[0]...laps[1]) : 3
}

struct GlyphsFile: Decodable {
    let dreams: [String: [String]]
    let heart: [String]
    let bang: [String]
    let heartColor: String
    let bangColor: String
    let dustColor: String
    enum CodingKeys: String, CodingKey {
        case dreams, heart, bang
        case heartColor = "heart_color", bangColor = "bang_color", dustColor = "dust_color"
    }
}

let glyphs = SharedData.decode(GlyphsFile.self, from: "glyphs")

let destructivePattern = #"\brm\s+(-\w*[rf]\w*\s+)+|\bmkfs|\bdd\s+if=|--force\b|\bpush\s+(-f|--force)|reset\s+--hard|\bdrop\s+(table|database)\b|\btruncate\s+table|\bsystem\s+prune|\bkill\s+-9|\bshutdown\b|\bchmod\s+-R\s+777|>\s*/dev/disk|\bdiskutil\s+erase"#
let thanksPattern = #"\b(thanks|thank\s*you|thx|ty|good\s*(boy|girl|dog|pup)|love\s*(you|u)|cute)\b"#

func matches(_ s: String?, _ pattern: String) -> Bool {
    guard let s else { return false }
    return s.range(of: pattern, options: [.regularExpression, .caseInsensitive]) != nil
}
