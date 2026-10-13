import Cocoa

let arguments = CommandLine.arguments
if arguments.count == 3 && arguments[1] == "--is-pet" {
    let id = arguments[2].lowercased()
    exit(allPets().contains { $0.id == id } ? 0 : 1)
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()
