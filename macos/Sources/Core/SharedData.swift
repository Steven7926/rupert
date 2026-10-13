import Foundation

enum SharedData {
    static let folder: URL = {
        guard let url = Bundle.main.resourceURL?.appendingPathComponent("shared"),
              FileManager.default.fileExists(atPath: url.appendingPathComponent("pets.json").path) else {
            fatalError("Rupert.app is missing its shared data. Build it with macos/build.sh.")
        }
        return url
    }()

    static func data(_ name: String) -> Data {
        guard let data = FileManager.default.contents(atPath: folder.appendingPathComponent("\(name).json").path) else {
            fatalError("Missing shared/\(name).json")
        }
        return data
    }

    static func decode<T: Decodable>(_ type: T.Type, from name: String) -> T {
        do {
            return try JSONDecoder().decode(T.self, from: data(name))
        } catch {
            fatalError("shared/\(name).json: \(error)")
        }
    }

    static func json(_ name: String) -> [String: Any] {
        (try? JSONSerialization.jsonObject(with: data(name))) as? [String: Any] ?? [:]
    }

    static func prompt(_ name: String) -> String {
        let url = folder.appendingPathComponent("prompts/\(name).txt")
        guard let text = try? String(contentsOf: url, encoding: .utf8) else { fatalError("Missing shared/prompts/\(name).txt") }
        return text.trimmingCharacters(in: .newlines)
    }

    static func fill(_ template: String, _ values: [String: String]) -> String {
        values.reduce(template) { $0.replacingOccurrences(of: "{{\($1.key.uppercased())}}", with: $1.value) }
    }
}
