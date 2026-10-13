import Carbon.HIToolbox
import Cocoa

final class AppDelegate: NSObject, NSApplicationDelegate, NSTextFieldDelegate, NSWindowDelegate {
    var pet = awakePet()

    var petPanel: Panel!
    var petView: PetView!
    var bubblePanel: Panel!
    var bubble: BubbleView!

    var history: [[String: String]] = []
    var busy = false
    var lastReply: String?

    var lastTarget: CGRect?
    var followedWindow = 0
    var followedRect: CGRect?
    var followedPid: pid_t = 0
    var ignoreWindow = 0
    var ignoreUntil = Date.distantPast
    var dockNap: (pid: pid_t, top: Int)?
    var pendingMinimize: (window: Int, until: Date, lastRect: CGRect?, tries: Int)?
    var lastSeen: (id: Int, rect: CGRect, since: Date) = (0, .zero, .distantPast)
    var spaceChangedAt = Date.distantPast
    var noWindowSince: Date?
    var dockRect: NSRect?
    let dock = DockLocator()

    var spot: CGFloat = 1
    var walkTarget: CGFloat = 1
    var track: CGFloat = 1
    var trackEdges: (CGFloat, CGFloat)?
    var nextWalk = Date().addingTimeInterval(Double.random(in: 20...60))
    var settleUntil = Date.distantPast
    var walkSpeed: CGFloat = defaultWalkSpeed
    var grab: CGFloat = 0
    var lapsLeft = 0
    var glideUntil = Date.distantPast
    var hiddenUntil: Date?
    var glideBetweenWindows = loadConfig()["glide"] as? Bool ?? true

    var hotKeyRef: EventHotKeyRef?
    var hotkeyNote = ""

    func applicationDidFinishLaunching(_ notification: Notification) {
        registerHotkey()
        setUpPetWindow()
        setUpBubble()

        let follow = Timer(timeInterval: 0.05, repeats: true) { [weak self] _ in self?.follow() }
        let animate = Timer(timeInterval: 0.1, repeats: true) { [weak self] _ in
            self?.petView.tick += 1
            self?.wander()
        }
        RunLoop.main.add(follow, forMode: .common)
        RunLoop.main.add(animate, forMode: .common)

        NSWorkspace.shared.notificationCenter.addObserver(
            forName: NSWorkspace.activeSpaceDidChangeNotification, object: nil, queue: .main) { [weak self] _ in
            self?.spaceChangedAt = Date()
            self?.dockNap = nil
        }
        NSEvent.addGlobalMonitorForEvents(matching: .leftMouseDown) { [weak self] _ in
            self?.endDockNap(at: NSEvent.mouseLocation)
            self?.watchForMinimizeClick(at: NSEvent.mouseLocation)
        }
    }

    private func setUpPetWindow() {
        let px = fullPx(pet)
        let size = NSSize(width: CGFloat(pet.w) * px + 10, height: CGFloat(pet.h) * px + 30)
        petPanel = Panel(size: size)
        petView = PetView(frame: NSRect(origin: .zero, size: size))
        petView.pet = pet
        petView.onClick = { [weak self] in self?.toggleBubble() }
        petView.onRightClick = { [weak self] e in self?.showMenu(e) }
        petView.onDragStart = { [weak self] x in self?.dragStart(x) ?? false }
        petView.onDrag = { [weak self] x in self?.drag(to: x) }
        petView.onDragEnd = { [weak self] in self?.dragEnd() }
        petView.onPetted = { [weak self] in self?.petted() }
        petPanel.contentView = petView
        petPanel.acceptsMouseMovedEvents = true
        if let vf = NSScreen.main?.visibleFrame {
            petPanel.setFrameOrigin(NSPoint(x: vf.maxX - 200, y: vf.minY + 40))
        }
        petPanel.orderFrontRegardless()
    }

    private func setUpBubble() {
        bubble = BubbleView(frame: .zero)
        bubble.input.target = self
        bubble.input.action = #selector(submit)
        bubble.input.delegate = self
        bubble.copyButton.target = self
        bubble.copyButton.action = #selector(copyAnswer)
        bubblePanel = Panel(size: bubble.frame.size)
        bubblePanel.contentView = bubble
        bubblePanel.allowsKey = true
        bubblePanel.delegate = self
    }

    func switchTo(_ newPet: Pet) {
        pet = newPet
        UserDefaults.standard.set(newPet.id, forKey: "dog")
        petView.pet = newPet
        lastTarget = nil
        follow()
        clearChat()
        bubble.setPlaceholder(askPrompt)
    }

    private func registerHotkey() {
        var spec = EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyPressed))
        InstallEventHandler(GetApplicationEventTarget(), { _, _, _ in
            DispatchQueue.main.async { (NSApp.delegate as? AppDelegate)?.hotkeyPressed() }
            return noErr
        }, 1, &spec, nil, nil)
        let id = EventHotKeyID(signature: OSType(0x5255_5054), id: 1)
        let status = RegisterEventHotKey(UInt32(kVK_ANSI_R), UInt32(controlKey | optionKey), id,
                                         GetApplicationEventTarget(), 0, &hotKeyRef)
        if status != noErr { hotkeyNote = "⌃⌥R is taken by another app" }
    }

    @objc func hotkeyPressed() {
        if bubblePanel.isVisible { closeBubble() } else { toggleBubble() }
    }
}
