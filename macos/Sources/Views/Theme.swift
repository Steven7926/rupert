import Cocoa

struct Theme: Decodable {
    let paper, border, text, muted, field, fieldEdge, accent, chip, chipText, button: String
    enum CodingKeys: String, CodingKey {
        case paper, border, text, muted, field, accent, chip, button
        case fieldEdge = "field_edge", chipText = "chip_text"
    }

    func color(_ key: KeyPath<Theme, String>) -> NSColor { hexColor(self[keyPath: key]) ?? .gray }
}

private struct ThemesFile: Decodable { let themes: [String: Theme] }

let themes = SharedData.decode(ThemesFile.self, from: "themes").themes
