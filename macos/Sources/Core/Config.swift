import Foundation

enum Paths {
    static let home = NSHomeDirectory() as NSString
    static let config = home.appendingPathComponent(".rupert_config.json")
    static let pets = home.appendingPathComponent(".rupert_pets.json")
    static let legacyKey = home.appendingPathComponent(".rupert_key")
}

typealias Config = [String: Any]

func loadConfig() -> Config {
    var cfg: Config = ["provider": "anthropic", "models": [String: String](), "vision_models": [String: String](),
                       "keys": [String: String](), "base_urls": [String: String]()]
    if let data = FileManager.default.contents(atPath: Paths.config),
       let saved = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
        if let p = saved["provider"] as? String, providerPresets.contains(where: { $0.id == p }) { cfg["provider"] = p }
        for k in ["models", "vision_models", "keys", "base_urls"] {
            if let d = saved[k] as? [String: String] { cfg[k] = d }
        }
        if let a = saved["appearance"] as? String { cfg["appearance"] = a }
        if let w = saved["wander"] as? Bool { cfg["wander"] = w }
        if let a = saved["activity"] as? String { cfg["activity"] = a }
        if let h = saved["hats"] as? [String: String] { cfg["hats"] = h }
        if let g = saved["glide"] as? Bool { cfg["glide"] = g }
    }
    var keys = cfg["keys"] as? [String: String] ?? [:]
    if keys["anthropic"] == nil,
       let old = (try? String(contentsOfFile: Paths.legacyKey, encoding: .utf8))?
           .trimmingCharacters(in: .whitespacesAndNewlines), !old.isEmpty {
        keys["anthropic"] = old
        cfg["keys"] = keys
    }
    return cfg
}

func saveConfig(_ cfg: Config) {
    if let data = try? JSONSerialization.data(withJSONObject: cfg, options: [.prettyPrinted]) {
        FileManager.default.createFile(atPath: Paths.config, contents: data,
                                       attributes: [.posixPermissions: 0o600])
    }
}

func setConfig(_ key: String, _ value: Any) {
    var cfg = loadConfig()
    cfg[key] = value
    saveConfig(cfg)
}

func setConfig(_ section: String, _ id: String, _ value: String) {
    var cfg = loadConfig()
    var d = cfg[section] as? [String: String] ?? [:]
    d[id] = value
    cfg[section] = d
    saveConfig(cfg)
}
