import Foundation

struct ProviderPreset: Decodable {
    let id: String, label: String, api: String, base: String
    let model: String?, vision: String?, env: String?
    let needsKey: Bool
    enum CodingKeys: String, CodingKey {
        case id, label, api, base, model, vision, env
        case needsKey = "needs_key"
    }
}

private struct ProvidersFile: Decodable {
    let providers: [ProviderPreset]
    let keyPrefixes: [[String]]
    let skipModels: [String]
    let fastHints: [String]
    enum CodingKeys: String, CodingKey {
        case providers
        case keyPrefixes = "key_prefixes", skipModels = "skip_models", fastHints = "fast_hints"
    }
}

private let providersFile = SharedData.decode(ProvidersFile.self, from: "providers")
let providerPresets = providersFile.providers
let localServers: Set<String> = ["custom", "ollama", "lmstudio"]

struct Provider {
    let id: String, label: String, api: String, key: String, base: String
    let needsKey: Bool, model: String, vision: String
    var ready: Bool { !base.isEmpty && !model.isEmpty && (!key.isEmpty || !needsKey) }
}

enum ProviderError: Error { case http(Int, String), network(String) }

func preset(_ id: String) -> ProviderPreset { providerPresets.first { $0.id == id } ?? providerPresets[0] }

func currentProvider() -> Provider {
    let cfg = loadConfig()
    let pre = preset(cfg["provider"] as? String ?? "anthropic")
    func get(_ section: String) -> String? { (cfg[section] as? [String: String])?[pre.id] }
    let envKey = pre.env.flatMap { ProcessInfo.processInfo.environment[$0] } ?? ""
    let model = get("models") ?? pre.model ?? ""
    var base = get("base_urls") ?? pre.base
    while base.hasSuffix("/") { base.removeLast() }
    return Provider(id: pre.id, label: pre.label, api: pre.api, key: envKey.isEmpty ? (get("keys") ?? "") : envKey,
                    base: base, needsKey: pre.needsKey, model: model,
                    vision: get("vision_models") ?? pre.vision ?? model)
}

func providerForKey(_ key: String, current: String) -> String {
    providersFile.keyPrefixes.first { $0.count == 2 && key.hasPrefix($0[0]) }?[1] ?? current
}

func looksLikeKey(_ s: String) -> Bool { s.count >= 20 && !s.contains(" ") }

func providerRequest(_ p: Provider, method: String, path: String, payload: [String: Any]?,
                     timeout: TimeInterval, done: @escaping (Result<Any, ProviderError>) -> Void) {
    guard let url = URL(string: p.base + path) else { done(.failure(.network("bad server URL"))); return }
    var req = URLRequest(url: url)
    req.httpMethod = method
    req.timeoutInterval = timeout
    req.setValue("application/json", forHTTPHeaderField: "content-type")
    if p.api == "anthropic" {
        req.setValue(p.key, forHTTPHeaderField: "x-api-key")
        req.setValue("2023-06-01", forHTTPHeaderField: "anthropic-version")
    } else if !p.key.isEmpty {
        req.setValue("Bearer \(p.key)", forHTTPHeaderField: "authorization")
    }
    if p.id == "openrouter" { req.setValue("Rupert desktop pet", forHTTPHeaderField: "x-title") }
    if let payload { req.httpBody = try? JSONSerialization.data(withJSONObject: payload) }
    URLSession.shared.dataTask(with: req) { data, resp, err in
        if let err {
            done(.failure(.network("can't reach \(p.label) (\(err.localizedDescription))")))
            return
        }
        let code = (resp as? HTTPURLResponse)?.statusCode ?? 0
        let json = data.flatMap { try? JSONSerialization.jsonObject(with: $0) }
        if (200..<300).contains(code), let json { done(.success(json)); return }
        var msg = data.flatMap { String(data: $0, encoding: .utf8) }.map { String($0.prefix(200)) } ?? ""
        if let d = (json as? [String: Any]) ?? (json as? [[String: Any]])?.first {
            if let e = d["error"] as? [String: Any], let m = e["message"] as? String { msg = m }
            else if let m = d["error"] as? String { msg = m }
        }
        done(.failure(.http(code, msg)))
    }.resume()
}

func chat(_ p: Provider, system: String?, messages: [[String: Any]], maxTokens: Int,
          model: String? = nil, imageB64: String? = nil, timeout: TimeInterval = 30,
          done: @escaping (Result<String, ProviderError>) -> Void) {
    var msgs = messages
    let m = model ?? p.model
    if p.api == "anthropic" {
        if let img = imageB64, var last = msgs.last {
            let source: [String: Any] = ["type": "base64", "media_type": "image/jpeg", "data": img]
            let parts: [[String: Any]] = [["type": "image", "source": source],
                                          ["type": "text", "text": last["content"] as? String ?? ""]]
            last["content"] = parts
            msgs[msgs.count - 1] = last
        }
        var payload: [String: Any] = ["model": m, "max_tokens": maxTokens, "messages": msgs]
        if let system { payload["system"] = system }
        providerRequest(p, method: "POST", path: "/messages", payload: payload, timeout: timeout) { r in
            done(r.map { json in
                ((json as? [String: Any])?["content"] as? [[String: Any]] ?? [])
                    .filter { $0["type"] as? String == "text" }.compactMap { $0["text"] as? String }.joined()
            })
        }
        return
    }
    if let img = imageB64, var last = msgs.last {
        let image: [String: Any] = ["url": "data:image/jpeg;base64,\(img)"]
        let parts: [[String: Any]] = [["type": "text", "text": last["content"] as? String ?? ""],
                                      ["type": "image_url", "image_url": image]]
        last["content"] = parts
        msgs[msgs.count - 1] = last
    }
    if let system { msgs.insert(["role": "system", "content": system], at: 0) }
    var payload: [String: Any] = ["model": m, "messages": msgs, "max_tokens": maxTokens]
    func parse(_ json: Any) -> String {
        let msg = ((json as? [String: Any])?["choices"] as? [[String: Any]])?.first?["message"] as? [String: Any]
        if let s = msg?["content"] as? String { return s }
        return (msg?["content"] as? [[String: Any]] ?? []).compactMap { $0["text"] as? String }.joined()
    }
    providerRequest(p, method: "POST", path: "/chat/completions", payload: payload, timeout: timeout) { r in
        if case .failure(.http(400, let msg)) = r, msg.contains("max_completion_tokens") {
            payload["max_completion_tokens"] = payload.removeValue(forKey: "max_tokens")
            providerRequest(p, method: "POST", path: "/chat/completions", payload: payload, timeout: timeout) {
                done($0.map(parse))
            }
        } else {
            done(r.map(parse))
        }
    }
}

func parseModelList(_ json: Any) -> [String] {
    let items = (json as? [String: Any]).flatMap { ($0["data"] ?? $0["models"]) as? [Any] } ?? (json as? [Any]) ?? []
    var ids = Set<String>()
    for item in items {
        guard var id = (item as? [String: Any]).flatMap({ ($0["id"] ?? $0["name"]) as? String })
                ?? (item as? String) else { continue }
        if id.hasPrefix("models/") { id = String(id.dropFirst(7)) }
        if !providersFile.skipModels.contains(where: { id.lowercased().contains($0) }) { ids.insert(id) }
    }
    return ids.sorted()
}

func listModels(_ p: Provider, done: @escaping ([String]) -> Void) {
    providerRequest(p, method: "GET", path: "/models", payload: nil, timeout: 10) { r in
        guard case .success(let json) = r else { done([]); return }
        done(parseModelList(json))
    }
}

func pickFastModel(_ ids: [String]) -> String {
    for hint in providersFile.fastHints {
        if let hit = ids.filter({ $0.lowercased().contains(hint) }).sorted().last { return hit }
    }
    return ids.first ?? ""
}

func friendlyError(_ e: ProviderError) -> String {
    switch e {
    case .http(401, _), .http(403, _): return "bad key. right-click → AI provider → Set API key."
    case .http(404, _): return "model not found. right-click → AI provider → Model."
    case .http(_, let m): return "grr. \(m.prefix(120))"
    case .network(let m): return "grr. \(m)"
    }
}

func connectProvider(done: @escaping (String) -> Void) {
    let p = currentProvider()
    listModels(p) { ids in
        if ids.isEmpty {
            DispatchQueue.main.async {
                done(p.ready ? "connected: \(p.label) · \(p.model)" : "can't list models. right-click → AI provider → Model.")
            }
            return
        }
        let chosen = (loadConfig()["models"] as? [String: String])?[p.id]
        if !(ids.contains(chosen ?? "") || ids.contains(preset(p.id).model ?? "")) {
            setConfig("models", p.id, pickFastModel(ids))
        }
        let now = currentProvider()
        DispatchQueue.main.async {
            done("connected: \(now.label.replacingOccurrences(of: "…", with: "")) · \(now.model)")
        }
    }
}
