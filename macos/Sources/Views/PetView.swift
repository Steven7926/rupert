import Cocoa

final class PetView: NSView {
    var pet = defaultPet { didSet { needsDisplay = true } }
    var awakeMode = false { didSet { needsDisplay = true } }
    var tick = 0 { didSet { needsDisplay = true } }
    var px: CGFloat = 4 { didSet { needsDisplay = true } }
    var compact = false { didSet { needsDisplay = true } }
    var mode = "sleep"
    var facing: CGFloat = 1
    var happyUntil = Date.distantPast
    var nervousUntil = Date.distantPast

    var onClick: (() -> Void)?
    var onRightClick: ((NSEvent) -> Void)?
    var onDragStart: ((CGFloat) -> Bool)?
    var onDrag: ((CGFloat) -> Void)?
    var onDragEnd: (() -> Void)?
    var onPetted: (() -> Void)?

    private var pressX: CGFloat?
    private var dragging = false
    private var moved = false
    private var rubs: [Date] = []
    private var hoverX: CGFloat?
    private var hoverDir: CGFloat = 0

    private static let heartColor = hexColor(glyphs.heartColor) ?? .systemPink
    private static let bangColor = hexColor(glyphs.bangColor) ?? .systemYellow
    private static let dustColor = hexColor(glyphs.dustColor) ?? .lightGray
    static let dustRoom: CGFloat = 22

    var paused: Bool { compact && (mode == "walk" || mode == "run") }
    var shown: String { paused ? "settle" : mode }

    var trail: CGFloat { shown == "run" ? Self.dustRoom : 0 }

    var spriteX: CGFloat {
        facing > 0 ? 4 + trail : bounds.width - 4 - trail - CGFloat(pet.w) * px
    }

    override var isFlipped: Bool { true }
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }

    private func currentFrame() -> (sprite: [String], hop: CGFloat, wiggle: CGFloat) {
        let now = Date(), t = tick
        if shown == "carry" { return (pet.awake[(t / 2) % pet.awake.count], 2 * px, 0) }
        if shown == "run" {
            let frames = pet.walk.isEmpty ? [pet.awake[0]] : pet.walk
            return (frames[t % frames.count], t % 2 == 1 ? px : 0, 0)
        }
        if now < nervousUntil && shown != "walk" {
            return (pet.awake[0], 0, t % 2 == 1 ? px / 2 : -px / 2)
        }
        if now < happyUntil && shown != "walk" {
            return (pet.awake[t % pet.awake.count], t % 4 == 0 ? px : 0, (t / 2) % 2 == 1 ? px : -px)
        }
        if awakeMode || shown == "settle" { return (pet.awake[(t / 2) % pet.awake.count], 0, 0) }
        if shown == "walk" && !pet.walk.isEmpty { return (pet.walk[(t / 2) % pet.walk.count], 0, 0) }
        if shown == "walk" { return (pet.awake[0], (t / 2) % 2 == 1 ? px : 0, 0) }
        return (pet.sleep[(t / 12) % pet.sleep.count], 0, 0)
    }

    override func draw(_ dirtyRect: NSRect) {
        NSColor.clear.set()
        dirtyRect.fill(using: .copy)
        NSGraphicsContext.current?.shouldAntialias = false

        let frame = currentFrame()
        let sprite = facing < 0 ? frame.sprite.map { String($0.reversed()) } : frame.sprite
        let ox = spriteX + frame.wiggle
        let top = bounds.height - CGFloat(sprite.count) * px - frame.hop
        if shown == "run" { drawDust(ox: ox) }

        pet.halo.setFill()
        for (y, line) in sprite.enumerated() {
            for (x, ch) in line.enumerated() where pet.palette[ch] != nil {
                NSRect(x: ox - 1 + CGFloat(x) * px, y: top - 1 + CGFloat(y) * px,
                       width: px + 2, height: px + 2).fill(using: .copy)
            }
        }
        for (y, line) in sprite.enumerated() {
            for (x, ch) in line.enumerated() {
                if let c = pet.palette[ch] { fill(ox + CGFloat(x) * px, top + CGFloat(y) * px, px, c) }
            }
        }

        let now = Date()
        if now < happyUntil {
            drawHearts(ox: ox, top: top)
        } else if now < nervousUntil {
            drawBang(ox: ox, top: top)
        } else if !awakeMode && shown == "sleep" {
            drawDreams(top: top)
        }
    }

    private func fill(_ x: CGFloat, _ y: CGFloat, _ s: CGFloat, _ c: NSColor) {
        c.setFill()
        NSRect(x: x, y: y, width: s, height: s).fill(using: .sourceOver)
    }

    private func drawGlyph(_ glyph: [String], x: CGFloat, y: CGFloat, size s: CGFloat, color: NSColor) {
        for (gy, row) in glyph.enumerated() {
            for (gx, ch) in row.enumerated() where ch == "K" { fill(x + CGFloat(gx) * s, y + CGFloat(gy) * s, s, color) }
        }
    }

    private func drawDust(ox: CGFloat) {
        let rear = facing > 0 ? ox : ox + CGFloat(pet.w) * px
        for i in 0..<3 {
            let t = CGFloat((tick + i * 3) % 9) / 9
            let s = px * (1.5 + t * 1.5)
            let x = facing > 0 ? rear - 3 - t * 16 - s : rear + 3 + t * 16
            fill(x, bounds.height - s - t * 6, s, Self.dustColor.withAlphaComponent(0.8 * (1 - t)))
        }
    }

    private func headX(_ ox: CGFloat) -> CGFloat { ox + (facing > 0 ? 0.75 : 0.25) * CGFloat(pet.w) * px }

    private func drawDreams(top: CGFloat) {
        let glyph = pet.dream
        guard let first = glyph.first else { return }
        for i in 0..<3 {
            let t = CGFloat((tick + i * 14) % 42) / 42
            let s: CGFloat = compact ? 1.5 : (t < 0.5 ? 2 : 2.5)
            var x = compact ? 4 + CGFloat(pet.w) * px + 2 + t * 12 : 4 + 0.75 * CGFloat(pet.w) * px + t * 16
            if facing < 0 { x = bounds.width - x - CGFloat(first.count) * s }
            let y = compact ? (bounds.height - CGFloat(glyph.count) * s - 1) * (1 - t) : top - 10 - t * 16
            drawGlyph(glyph, x: x, y: y, size: s, color: pet.dreamColor.withAlphaComponent(1 - t))
        }
    }

    private func drawHearts(ox: CGFloat, top: CGFloat) {
        let head = headX(ox)
        for i in 0..<3 {
            let t = CGFloat((tick * 2 + i * 9) % 27) / 27
            let s: CGFloat = compact ? 1 : 1.5
            let x = head + CGFloat(i - 1) * 9 + t * 4 * (i % 2 == 1 ? 1 : -1)
            let y = compact ? (bounds.height - 8 * s) * (1 - t) : top - 6 - t * 20
            drawGlyph(glyphs.heart, x: x, y: y, size: s, color: Self.heartColor.withAlphaComponent(max(0, 1 - t * t)))
        }
    }

    private func drawBang(ox: CGFloat, top: CGFloat) {
        let s: CGFloat = compact ? 1.5 : 2
        let y = (compact ? 1 : top - 16) - ((tick / 2) % 2 == 1 ? 2 : 0)
        drawGlyph(glyphs.bang, x: headX(ox) - s, y: y, size: s, color: Self.bangColor)
    }

    override func updateTrackingAreas() {
        super.updateTrackingAreas()
        trackingAreas.forEach { removeTrackingArea($0) }
        addTrackingArea(NSTrackingArea(rect: .zero, options: [.mouseMoved, .mouseEnteredAndExited,
                                                             .activeAlways, .inVisibleRect],
                                       owner: self, userInfo: nil))
    }

    override func mouseMoved(with event: NSEvent) {
        let x = NSEvent.mouseLocation.x
        if let last = hoverX, abs(x - last) >= 3 {
            let d: CGFloat = x > last ? 1 : -1
            if hoverDir != 0 && d != hoverDir {
                let now = Date()
                rubs = rubs.filter { now.timeIntervalSince($0) < 1.5 } + [now]
                if rubs.count >= 3 { onPetted?() }
            }
            hoverDir = d
        }
        if hoverX == nil || abs(x - (hoverX ?? x)) >= 3 { hoverX = x }
    }

    override func mouseExited(with event: NSEvent) { hoverX = nil; hoverDir = 0 }

    override func mouseDown(with event: NSEvent) {
        pressX = NSEvent.mouseLocation.x
        dragging = false
        moved = false
    }

    override func mouseDragged(with event: NSEvent) {
        guard let start = pressX else { return }
        let x = NSEvent.mouseLocation.x
        if !moved && abs(x - start) > 4 { moved = true; dragging = onDragStart?(start) ?? false }
        if dragging { onDrag?(x) }
    }

    override func mouseUp(with event: NSEvent) {
        if dragging { onDragEnd?() } else if pressX != nil && !moved { onClick?() }
        pressX = nil
        dragging = false
    }

    override func rightMouseDown(with event: NSEvent) { onRightClick?(event) }
}
