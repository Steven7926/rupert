import Cocoa

final class BubbleView: NSView {
    let input = NSTextField()
    let answer = NSTextField(wrappingLabelWithString: "")
    let copyButton = HandButton()
    let width: CGFloat = 300
    let tailH: CGFloat = 10
    var tailDown = true { didSet { if tailDown != oldValue { relayout() } } }
    var tailX: CGFloat = 250 { didSet { needsDisplay = true } }
    private(set) var theme = themes["light"]!
    private var raw: (text: String, command: String?) = ("", nil)
    private var placeholder = "ask…"
    private var copied = false
    private var cmdLine = 0

    static let maxInputLines: CGFloat = 5
    private let font = NSFont.monospacedSystemFont(ofSize: 13, weight: .medium)
    private let boldFont = NSFont.monospacedSystemFont(ofSize: 13, weight: .bold)
    private var lineHeight: CGFloat { NSLayoutManager().defaultLineHeight(for: font) }

    override init(frame: NSRect) {
        super.init(frame: frame)
        input.font = font
        input.isBezeled = false
        input.isBordered = false
        input.drawsBackground = false
        input.focusRingType = .none
        input.placeholderString = placeholder
        input.cell?.isScrollable = false
        input.cell?.wraps = true
        input.usesSingleLineMode = false
        input.lineBreakMode = .byWordWrapping

        answer.font = font
        answer.isSelectable = true
        answer.maximumNumberOfLines = 0

        copyButton.isBordered = false
        copyButton.imagePosition = .imageOnly
        copyButton.imageScaling = .scaleProportionallyDown
        copyButton.toolTip = "Copy command"
        copyButton.isHidden = true

        addSubview(answer)
        addSubview(input)
        addSubview(copyButton)
        applyTheme("light")
    }

    required init?(coder: NSCoder) { fatalError("not used") }

    func applyTheme(_ name: String) {
        theme = themes[name] ?? themes["light"]!
        appearance = NSAppearance(named: name == "dark" ? .darkAqua : .aqua)
        input.textColor = theme.color(\.text)
        setPlaceholder(placeholder)
        showCopied(copied)
        setAnswer(raw.text, command: raw.command)
    }

    func setPlaceholder(_ s: String) {
        placeholder = s
        input.placeholderAttributedString = NSAttributedString(string: s, attributes: [
            .foregroundColor: theme.color(\.muted), .font: font])
    }

    func showCopied(_ done: Bool) {
        copied = done
        let cfg = NSImage.SymbolConfiguration(pointSize: 11, weight: .semibold)
        copyButton.image = NSImage(systemSymbolName: done ? "checkmark" : "doc.on.clipboard",
                                   accessibilityDescription: "Copy command")?.withSymbolConfiguration(cfg)
        copyButton.contentTintColor = theme.color(\.accent)
    }

    func setAnswer(_ s: String, command: String? = nil) {
        raw = (s, command)
        var lines = s.components(separatedBy: "\n")
        cmdLine = 0
        if command != nil && lines.count > 1 {
            lines = Array(lines.dropFirst()) + [lines[0]]
            cmdLine = lines.count - 1
        }
        if let cmd = command, let r = lines[cmdLine].range(of: cmd) {
            lines[cmdLine].insert(contentsOf: "    ", at: r.upperBound)
        }
        let text = NSMutableAttributedString(string: lines.joined(separator: "\n"),
                                             attributes: [.font: font, .foregroundColor: theme.color(\.text)])
        if let cmd = command {
            let start = lines[..<cmdLine].reduce(0) { $0 + ($1 as NSString).length + 1 }
            let r = (lines[cmdLine] as NSString).range(of: cmd)
            if r.location != NSNotFound {
                text.addAttributes([.font: boldFont, .backgroundColor: theme.color(\.chip),
                                    .foregroundColor: theme.color(\.chipText)],
                                   range: NSRange(location: start + r.location, length: r.length))
            }
        }
        answer.attributedStringValue = text
        relayout()
    }

    func inputHeight(width w: CGFloat) -> CGFloat {
        let text = input.currentEditor()?.string ?? input.stringValue
        let r = NSAttributedString(string: text.isEmpty ? " " : text + (text.hasSuffix("\n") ? " " : ""),
                                   attributes: [.font: font])
            .boundingRect(with: NSSize(width: w - 4, height: .greatestFiniteMagnitude),
                          options: [.usesLineFragmentOrigin, .usesFontLeading])
        return max(20, min(ceil(r.height) + 4, lineHeight * Self.maxInputLines + 4))
    }

    static let edge: CGFloat = 14
    static let gap: CGFloat = 10
    static let wellPad: CGFloat = 3
    static let promptRoom: CGFloat = 18

    private var contentWidth: CGFloat { width - Self.edge * 2 }

    func relayout() {
        let edge = Self.edge, inner = contentWidth
        let inputW = inner - Self.promptRoom - 4
        let inputH = inputHeight(width: inputW)
        var answerW = inner
        var clipX: CGFloat?
        if !copyButton.isHidden, let cmd = raw.command {
            let chipW = NSAttributedString(string: cmd, attributes: [.font: boldFont]).size().width
            if chipW + 26 <= inner { clipX = edge + chipW + 4 } else { answerW = inner - 22; clipX = edge + answerW + 2 }
        }
        var answerH: CGFloat = 0
        if !answer.stringValue.isEmpty, let cell = answer.cell {
            answerH = ceil(cell.cellSize(forBounds: NSRect(x: 0, y: 0, width: answerW, height: 10_000)).height)
        }
        let wellH = inputH + Self.wellPad * 2
        let answerBlock = answerH > 0 ? Self.gap + answerH : 0
        setFrameSize(NSSize(width: width, height: tailH + edge + wellH + answerBlock + edge))
        let base: CGFloat = tailDown ? tailH : 0
        input.frame = NSRect(x: edge + Self.promptRoom, y: base + edge + Self.wellPad, width: inputW, height: inputH)
        answer.isHidden = answerH == 0
        answer.frame = NSRect(x: edge, y: base + edge + wellH + Self.gap, width: answerW, height: answerH)
        if let x = clipX {
            let lineTop = answer.frame.maxY - CGFloat(cmdLine) * lineHeight
            copyButton.frame = NSRect(x: x, y: lineTop - lineHeight + (lineHeight - 18) / 2 - 1, width: 18, height: 18)
        }
        needsDisplay = true
    }

    override func draw(_ dirtyRect: NSRect) {
        NSColor.clear.set()
        dirtyRect.fill(using: .copy)
        let paper = theme.color(\.paper), ink = theme.color(\.border)
        var body = bounds
        body.size.height -= tailH
        if tailDown { body.origin.y += tailH }
        body = body.insetBy(dx: 1.5, dy: 1.5)
        let shape = NSBezierPath(roundedRect: body, xRadius: 10, yRadius: 10)
        paper.setFill(); shape.fill()
        ink.setStroke(); shape.lineWidth = 3; shape.stroke()

        let tx = min(max(tailX, 22), width - 22), half: CGFloat = 9
        let edge = tailDown ? body.minY : body.maxY
        let tip = tailDown ? edge - tailH + 1.5 : edge + tailH - 1.5
        let tail = NSBezierPath()
        tail.move(to: NSPoint(x: tx - half, y: edge))
        tail.line(to: NSPoint(x: tx, y: tip))
        tail.line(to: NSPoint(x: tx + half, y: edge))
        paper.setFill(); tail.fill()
        tail.lineWidth = 3; tail.lineJoinStyle = .round; ink.setStroke(); tail.stroke()
        paper.setFill()
        NSRect(x: tx - half + 2.5, y: edge - 2, width: half * 2 - 5, height: 4).fill()

        let f = input.frame
        let well = NSBezierPath(roundedRect: NSRect(x: Self.edge, y: f.minY - Self.wellPad, width: contentWidth,
                                                    height: f.height + Self.wellPad * 2),
                                xRadius: 7, yRadius: 7)
        theme.color(\.field).setFill(); well.fill()
        (window?.isKeyWindow == true ? theme.color(\.accent) : theme.color(\.fieldEdge)).setStroke()
        well.lineWidth = 1.5; well.stroke()
        let caret = NSAttributedString(string: "›", attributes: [
            .foregroundColor: theme.color(\.accent), .font: NSFont.monospacedSystemFont(ofSize: 14, weight: .bold)])
        let caretLine = lineHeight + 4
        caret.draw(at: NSPoint(x: Self.edge + 5, y: f.maxY - caretLine + (caretLine - caret.size().height) / 2))
    }
}
