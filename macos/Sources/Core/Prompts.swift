import Foundation

let cavemanRules = SharedData.prompt("caveman")

func petPrompt(name: String, description: String, personality: String, flavor: [String]) -> String {
    let fl = flavor + ["hmm.", "ok."]
    return SharedData.fill(SharedData.prompt("pet"), [
        "name": name, "description": description, "personality": personality,
        "os_note": "The user is on macOS.", "caveman_rules": cavemanRules,
        "flavor_1": fl[0], "flavor_2": fl[1],
    ])
}

func drawPetPrompt(name: String, example sprite: [String: Any]) -> String {
    let example: [String: Any] = ["palette": sprite["palette"] ?? [String: String](),
                                  "asleep": sprite["asleep"] ?? [String]()]
    let json = (try? JSONSerialization.data(withJSONObject: example)).flatMap { String(data: $0, encoding: .utf8) } ?? "{}"
    return SharedData.fill(SharedData.prompt("draw_pet"), ["name": name, "example": json])
}

func timeNote() -> String {
    let f = DateFormatter()
    f.dateFormat = "h:mm a 'on' EEEE"
    return "\nIt is \(f.string(from: Date())) for the user. If it's very late at night, your extra line "
        + "may tell them to go to bed; early morning, you can be sleepy."
}

func tighten(_ raw: String) -> String {
    let raw = raw.replacingOccurrences(of: "(?s)<think>.*?(</think>|$)", with: "", options: .regularExpression)
    let lines = raw.replacingOccurrences(of: "`", with: "")
        .split(separator: "\n").map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }
    guard let answer = lines.first else { return "" }
    guard lines.count > 1 else { return answer }
    return answer + "\n" + lines[1].split(separator: " ").prefix(2).joined(separator: " ")
}

func commandPart(_ reply: String) -> String? {
    guard let line = reply.split(separator: "\n").first else { return nil }
    let cmd = line.components(separatedBy: " — ").first?.trimmingCharacters(in: .whitespaces) ?? ""
    return cmd.isEmpty || cmd.hasSuffix("?") ? nil : cmd
}
