import Cocoa

extension AppDelegate {
    func place(on r: CGRect, force: Bool = false) {
        guard r != lastTarget || force else { return }
        let prev: CGRect? = force ? r : lastTarget
        lastTarget = r
        let primaryH = NSScreen.screens.first?.frame.height ?? 0
        let windowTop = primaryH - r.minY
        let cocoa = NSRect(x: r.minX, y: primaryH - r.maxY, width: r.width, height: r.height)
        let screen = NSScreen.screens.first { $0.frame.intersects(cocoa) } ?? NSScreen.main

        let visibleTop = screen?.visibleFrame.maxY ?? .infinity
        let menuH = screen.map { $0.frame.maxY - $0.visibleFrame.maxY } ?? 0
        let ceiling = menuH >= 18 ? (screen?.frame.maxY ?? visibleTop) : visibleTop
        let room = ceiling - windowTop
        let sw = CGFloat(pet.w), sh = CGFloat(pet.h), topPx = fullPx(pet)
        let px = max(1, min(topPx, ((room - 2) / sh * 2).rounded(.down) / 2))
        let bodyH = sh * px

        let y = min(windowTop - 1, ceiling - bodyH - 1)
        let left = r.minX + 14, right = r.maxX - sw * px - 14
        track = max(1, right - left)
        trackEdges = (left, right)
        var sx = left + spot * (right - left)

        let compact = px < topPx || visibleTop - (y + bodyH) < 26
        let trail = petView.mode == "run" && !compact ? PetView.dustRoom : 0
        let size = compact ? NSSize(width: sw * px + 26 + trail, height: bodyH + 2)
                           : NSSize(width: sw * px + 10 + trail, height: bodyH + 30)
        let overMenuBar = y + bodyH > visibleTop
        if overMenuBar { sx = max(sx, min(right, screen?.frame.midX ?? left)) }
        let x = max(r.minX - 4 - trail, petView.facing > 0 ? sx - 4 - trail : sx - (size.width - 4 - trail - sw * px))

        let glide = glideBetweenWindows && hiddenUntil == nil && (prev.map { $0.origin != r.origin && $0.size != r.size } ?? false)
        if !force { debugLog("place on \(describe(r)) compact \(compact) glide \(glide)") }
        setMode(px: px, compact: compact, level: overMenuBar ? .statusBar : .floating,
                frame: NSRect(origin: NSPoint(x: x, y: y), size: size), glide: glide)
    }

    func setMode(px: CGFloat, compact: Bool, level: NSWindow.Level, frame: NSRect, glide: Bool) {
        petView.px = px
        petView.compact = compact
        petPanel.level = level
        bubblePanel.level = level
        if glide { glideUntil = Date().addingTimeInterval(0.22) }
        let remaining = glideUntil.timeIntervalSinceNow
        if remaining > 0.02 {
            NSAnimationContext.runAnimationGroup({ ctx in
                ctx.duration = remaining
                ctx.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
                petPanel.animator().setFrame(frame, display: true)
            }, completionHandler: { [weak self] in self?.positionBubble() })
        } else {
            petPanel.setFrame(frame, display: true)
            positionBubble()
        }
    }

    func positionBubble() {
        guard bubblePanel.isVisible else { return }
        let d = petPanel.frame, b = bubblePanel.frame.size
        let spriteW = CGFloat(pet.w) * petView.px
        let spriteLeft = d.minX + petView.spriteX
        let headX = spriteLeft + (petView.facing > 0 ? 0.8 : 0.2) * spriteW
        let headTop = d.minY + CGFloat(pet.h) * petView.px
        var x = headX - b.width + 40
        var y = headTop + 2
        var down = true
        if let vf = (petPanel.screen ?? NSScreen.main)?.visibleFrame {
            if y + b.height > vf.maxY { y = d.minY - b.height - 2; down = false }
            x = min(max(x, vf.minX + 4), vf.maxX - b.width - 4)
        }
        bubble.tailDown = down
        bubble.tailX = headX - x
        bubblePanel.setFrameOrigin(NSPoint(x: x, y: y))
    }
}
