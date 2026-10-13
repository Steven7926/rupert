import Cocoa

extension AppDelegate {
    func wander() {
        let now = Date()
        switch petView.mode {
        case "walk", "run":
            if bubblePanel.isVisible { petView.mode = "sleep"; lapsLeft = 0; return }
            if petView.paused { return }
            let step = walkSpeed / 10 / max(1, track)
            spot += max(-step, min(step, walkTarget - spot))
            if abs(walkTarget - spot) < 0.001 {
                if petView.mode == "run" && lapsLeft > 0 {
                    lapsLeft -= 1
                    runLeg(-petView.facing)
                } else {
                    settleUntil = now.addingTimeInterval(petView.mode == "run" ? 3 : 1.2)
                    petView.mode = "settle"
                }
            }
            replace()
        case "settle" where now > settleUntil:
            petView.mode = "sleep"
            scheduleWalk()
        case "sleep" where now > nextWalk && !bubblePanel.isVisible && !petView.compact && lastTarget != nil:
            let mode = activityMode(loadConfig())
            let (gap, speed) = walkPlan(mode)
            walkSpeed = speed
            guard gap != nil else { nextWalk = now.addingTimeInterval(300); return }
            if Double.random(in: 0..<1) < zoomiesChance(mode: mode, walkSpeed: speed, energy: pet.energy) {
                startZoomies()
                return
            }
            let options = (0...20).map { CGFloat($0) / 20 }.filter { abs($0 - spot) >= 0.25 }
            walkTarget = options.randomElement() ?? 0.5
            petView.facing = walkTarget > spot ? 1 : -1
            petView.mode = "walk"
            replace()
        default:
            break
        }
    }

    func startZoomies() {
        walkSpeed = zoomiesSpeed
        lapsLeft = zoomiesLaps() - 1
        petView.mode = "run"
        runLeg(spot > 0.5 ? -1 : 1)
        replace()
    }

    private func runLeg(_ direction: CGFloat) {
        walkTarget = zoomiesTarget(spot: spot, direction: direction)
        petView.facing = walkTarget > spot ? 1 : -1
    }

    func scheduleWalk(atLeast: Double = 0) {
        let (gap, _) = walkPlan(activityMode(loadConfig()))
        let now = Date()
        nextWalk = max(nextWalk, now.addingTimeInterval(atLeast), now.addingTimeInterval(gap ?? 300))
    }

    func replace() { if let r = lastTarget { place(on: r, force: true) } }

    func dragStart(_ x: CGFloat) -> Bool {
        guard trackEdges != nil else { return false }
        lapsLeft = 0
        grab = x - (petPanel.frame.minX + petView.spriteX)
        petView.mode = "carry"
        return true
    }

    func drag(to x: CGFloat) {
        guard let edges = trackEdges else { return }
        let (left, right) = edges
        spot = max(0, min(1, (x - grab - left) / max(1, right - left)))
        walkTarget = spot
        replace()
    }

    func dragEnd() {
        petView.mode = "settle"
        settleUntil = Date().addingTimeInterval(1.0)
        nextWalk = Date()
        scheduleWalk(atLeast: 180)
    }
}
