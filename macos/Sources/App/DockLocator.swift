import Cocoa

final class DockLocator {
    private var cache: (at: Date, screen: NSRect, rect: NSRect?)?

    func frame(on screen: NSScreen) -> NSRect? {
        if let c = cache, c.screen == screen.frame, Date().timeIntervalSince(c.at) < 2 { return c.rect }
        let f = screen.frame, vf = screen.visibleFrame
        var rect: NSRect?
        let dockH = vf.minY - f.minY
        if dockH > 12 {
            if AXIsProcessTrusted(), let r = accessibilityFrame(), r.width > 40 {
                let primaryH = NSScreen.screens.first?.frame.height ?? 0
                rect = NSRect(x: r.minX, y: primaryH - r.maxY, width: r.width, height: r.height)
            } else {
                let w = min(f.width, estimatedWidth(dockHeight: dockH))
                rect = NSRect(x: f.midX - w / 2, y: f.minY, width: w, height: dockH)
            }
        }
        cache = (Date(), screen.frame, rect)
        return rect
    }

    private func accessibilityFrame() -> CGRect? {
        guard let dock = NSRunningApplication.runningApplications(withBundleIdentifier: "com.apple.dock").first
        else { return nil }
        let app = AXUIElementCreateApplication(dock.processIdentifier)
        var kids: CFTypeRef?
        guard AXUIElementCopyAttributeValue(app, kAXChildrenAttribute as CFString, &kids) == .success,
              let list = (kids as? [AXUIElement])?.first else { return nil }
        var pos: CFTypeRef?, size: CFTypeRef?
        guard AXUIElementCopyAttributeValue(list, kAXPositionAttribute as CFString, &pos) == .success,
              AXUIElementCopyAttributeValue(list, kAXSizeAttribute as CFString, &size) == .success,
              let pos, let size, CFGetTypeID(pos) == AXValueGetTypeID(), CFGetTypeID(size) == AXValueGetTypeID()
        else { return nil }
        var p = CGPoint.zero, s = CGSize.zero
        AXValueGetValue(pos as! AXValue, .cgPoint, &p)
        AXValueGetValue(size as! AXValue, .cgSize, &s)
        return CGRect(origin: p, size: s)
    }

    private func estimatedWidth(dockHeight: CGFloat) -> CGFloat {
        let d = UserDefaults(suiteName: "com.apple.dock")
        let apps = d?.array(forKey: "persistent-apps") as? [[String: Any]] ?? []
        let others = d?.array(forKey: "persistent-others")?.count ?? 0
        let pinned = Set(apps.compactMap { ($0["tile-data"] as? [String: Any])?["bundle-identifier"] as? String })
        let running = NSWorkspace.shared.runningApplications.filter {
            $0.activationPolicy == .regular && $0.bundleIdentifier != "com.apple.finder" &&
                !pinned.contains($0.bundleIdentifier ?? "")
        }.count
        let showRecents = d?.object(forKey: "show-recents") as? Bool ?? true
        let recents = showRecents ? min(3, d?.array(forKey: "recent-apps")?.count ?? 0) : 0
        let extra = max(running, recents)
        let tiles = CGFloat(1 + apps.count + extra + others + 1)
        let dividers: CGFloat = extra > 0 ? 2 : 1
        let saved = d?.double(forKey: "tilesize") ?? 0
        let tile = saved > 8 ? CGFloat(saved) : max(16, dockHeight - 14)
        return tiles * tile + dividers * tile * 0.35 + tile * 0.4
    }
}
