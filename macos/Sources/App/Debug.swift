import Foundation

let debugEnabled = UserDefaults.standard.bool(forKey: "debug")
let debugLogPath = (NSHomeDirectory() as NSString).appendingPathComponent("Library/Logs/Rupert.log")
private let debugStart = Date()

func debugLog(_ message: @autoclosure () -> String) {
    guard debugEnabled else { return }
    let line = String(format: "%8.3f  ", Date().timeIntervalSince(debugStart)) + message() + "\n"
    guard let data = line.data(using: .utf8) else { return }
    if let handle = FileHandle(forWritingAtPath: debugLogPath) {
        handle.seekToEndOfFile()
        handle.write(data)
        handle.closeFile()
    } else {
        FileManager.default.createFile(atPath: debugLogPath, contents: data)
    }
}

func describe(_ r: CGRect) -> String {
    String(format: "(x %.0f y %.0f w %.0f h %.0f)", r.minX, r.minY, r.width, r.height)
}
