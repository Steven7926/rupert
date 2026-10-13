import Cocoa

let minimizeAnimation = 0.55
let minimizeCheck = 1.0
let shrinkHint: CGFloat = 0.97
let settleTime = 0.15
let minimizeButton = CGRect(x: 25, y: 0, width: 21, height: 56)

extension AppDelegate {
    func follow() {
        reappearIfReady()
        guard let app = NSWorkspace.shared.frontmostApplication,
              app.processIdentifier != getpid(),
              let list = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements],
                                                    kCGNullWindowID) as? [[String: Any]]
        else { return }
        let pid = app.processIdentifier

        var wins: [CGRect] = []
        var ids: [Int] = []
        for w in list {
            guard (w[kCGWindowOwnerPID as String] as? NSNumber)?.int32Value == pid,
                  (w[kCGWindowLayer as String] as? NSNumber)?.intValue == 0,
                  ((w[kCGWindowAlpha as String] as? NSNumber)?.doubleValue ?? 1) > 0.1,
                  let dict = w[kCGWindowBounds as String] as? NSDictionary,
                  let r = CGRect(dictionaryRepresentation: dict as CFDictionary),
                  r.width > 140, r.height > 60
            else { continue }
            let num = (w[kCGWindowNumber as String] as? NSNumber)?.intValue ?? 0
            if num == ignoreWindow && Date() < ignoreUntil { continue }
            wins.append(r)
            ids.append(num)
        }

        let top = wins.indices.first { i in !wins[(i + 1)...].contains { r in r != wins[i] && r.contains(wins[i]) } }
        let topId = top.map { ids[$0] } ?? 0

        if let check = pendingMinimize, Date() >= check.until { confirmMinimize(check) }

        if let nap = dockNap {
            if nap.pid == pid && nap.top == -1 { dockNap = (pid, topId); park(); return }
            if nap.pid == pid && (topId == nap.top || topId == 0) { park(); return }
            dockNap = nil
        }

        var shrinking = false
        if let i = top, ids[i] == followedWindow, let b = followedRect, NSEvent.pressedMouseButtons == 0 {
            shrinking = looksLikeMinimizing(from: b, to: wins[i])
            if wins[i] != b { debugLog("window \(ids[i]) \(describe(b)) -> \(describe(wins[i])) minimizing: \(shrinking)") }
        }
        let switchedSpace = Date().timeIntervalSince(spaceChangedAt) < 1
        if followedWindow != 0 && followedPid == pid && !switchedSpace &&
            (shrinking || (!ids.contains(followedWindow) && isMinimized(followedWindow))) {
            goToDock(nextTop: shrinking ? -1 : topId)
            return
        }

        if let i = top {
            noWindowSince = nil
            if ids[i] != lastSeen.id || wins[i] != lastSeen.rect { lastSeen = (ids[i], wins[i], Date()) }
            let settled = Date().timeIntervalSince(lastSeen.since) >= settleTime
            guard settled || NSEvent.pressedMouseButtons != 0 else { return }
            followedWindow = ids[i]; followedRect = wins[i]; followedPid = pid
            place(on: wins[i])
            return
        }
        parkIfNoWindow()
    }

    func looksLikeMinimizing(from old: CGRect, to new: CGRect) -> Bool {
        let notGrowing = new.width <= old.width + 1 && new.height <= old.height + 1
        let narrower = new.width < old.width * shrinkHint
        let shorter = new.height < old.height * shrinkHint
        let topDropped = new.minY > old.minY + 4
        return notGrowing && ((narrower && shorter) || (shorter && topDropped))
    }

    func goToDock(nextTop: Int) {
        debugLog("go to dock (window \(followedWindow), glide \(glideBetweenWindows))")
        let window = followedWindow
        ignoreWindow = window
        ignoreUntil = Date().addingTimeInterval(minimizeCheck + 0.5)
        followedWindow = 0; followedRect = nil
        dockNap = (followedPid, nextTop)
        pendingMinimize = (window, Date().addingTimeInterval(minimizeCheck), nil, 0)
        if glideBetweenWindows { vanish(for: minimizeAnimation) } else { glideUntil = .distantPast }
        park()
    }

    func confirmMinimize(_ check: (window: Int, until: Date, lastRect: CGRect?, tries: Int)) {
        let state = windowState(check.window)
        if !state.onscreen {
            debugLog("check window \(check.window): gone from screen, staying on the dock")
            pendingMinimize = nil
            ignoreWindow = 0
        } else if let rect = state.rect, rect == check.lastRect || check.tries >= 6 {
            debugLog("check window \(check.window): still on screen at \(describe(rect)), going back")
            pendingMinimize = nil
            dockNap = nil
            ignoreWindow = 0
        } else {
            pendingMinimize = (check.window, Date().addingTimeInterval(0.25), state.rect, check.tries + 1)
        }
    }

    func windowState(_ windowNumber: Int) -> (onscreen: Bool, rect: CGRect?) {
        guard let info = CGWindowListCopyWindowInfo(.optionIncludingWindow, CGWindowID(windowNumber)) as? [[String: Any]],
              let w = info.first else { return (false, nil) }
        let bounds = (w[kCGWindowBounds as String] as? NSDictionary).flatMap { CGRect(dictionaryRepresentation: $0 as CFDictionary) }
        return ((w[kCGWindowIsOnscreen as String] as? Bool) == true, bounds)
    }

    func vanish(for seconds: Double) {
        let until = Date().addingTimeInterval(seconds)
        hiddenUntil = max(hiddenUntil ?? until, until)
        glideUntil = .distantPast
        petPanel.alphaValue = 0
        if bubblePanel.isVisible { closeBubble() }
    }

    func reappearIfReady() {
        guard let until = hiddenUntil, Date() >= until else { return }
        hiddenUntil = nil
        NSAnimationContext.runAnimationGroup { ctx in
            ctx.duration = 0.12
            petPanel.animator().alphaValue = 1
        }
    }

    func watchForMinimizeClick(at p: NSPoint) {
        guard followedWindow != 0, dockNap == nil, let r = followedRect,
              NSWorkspace.shared.frontmostApplication?.processIdentifier == followedPid else { return }
        let primaryH = NSScreen.screens.first?.frame.height ?? 0
        let x = p.x - r.minX, y = primaryH - p.y - r.minY
        let hit = minimizeButton.contains(CGPoint(x: x, y: y))
        if y < 80 && x < 120 { debugLog(String(format: "click at %.0f, %.0f in window: minimize button %@", x, y, hit ? "yes" : "no")) }
        if hit { goToDock(nextTop: -1) }
    }

    func isMinimized(_ windowNumber: Int) -> Bool {
        guard let info = CGWindowListCopyWindowInfo(.optionIncludingWindow, CGWindowID(windowNumber)) as? [[String: Any]],
              let w = info.first else { return false }
        return (w[kCGWindowIsOnscreen as String] as? Bool) != true
    }

    func endDockNap(at p: NSPoint) {
        guard dockNap != nil, let dock = dockRect, !dock.insetBy(dx: -4, dy: -20).contains(p),
              !petPanel.frame.contains(p) else { return }
        dockNap = nil
    }

    func parkIfNoWindow() {
        let now = Date()
        guard let since = noWindowSince else { noWindowSince = now; return }
        guard now.timeIntervalSince(since) > 0.15 else { return }
        park()
    }

    func park() {
        guard let screen = NSScreen.main ?? petPanel.screen else { return }
        let primaryH = NSScreen.screens.first?.frame.height ?? 0
        let vf = screen.visibleFrame
        dockRect = dock.frame(on: screen)
        let base = dockRect ?? vf
        let floor = CGRect(x: base.minX, y: primaryH - vf.minY, width: base.width, height: 1)
        if lastTarget != floor { place(on: floor) }
    }
}
