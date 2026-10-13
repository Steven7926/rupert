import Cocoa
import UniformTypeIdentifiers

func spriteImage(_ rows: [String], palette: [Character: NSColor], px: CGFloat) -> NSImage {
    let w = CGFloat(rows.map(\.count).max() ?? 1), h = CGFloat(rows.count)
    return NSImage(size: NSSize(width: w * px, height: h * px), flipped: true) { _ in
        for (y, line) in rows.enumerated() {
            for (x, ch) in line.enumerated() {
                if let c = palette[ch] {
                    c.setFill()
                    NSRect(x: CGFloat(x) * px, y: CGFloat(y) * px, width: px, height: px).fill()
                }
            }
        }
        return true
    }
}

struct PetChoice {
    let name: String
    let fromPhoto: Bool
    let photoURL: URL?
    let breed: String, color: String
    let personality: String
}

final class PetForm: NSObject, NSTextFieldDelegate {
    static let maxName = 24

    let existing: SavedPet?
    private(set) var photoURL: URL?
    let view = FlippedView(frame: NSRect(x: 0, y: 0, width: 420, height: 352))
    let name = NSTextField()
    weak var okButton: NSButton?

    private let preview = NSImageView()
    private let previewNote = NSTextField(labelWithString: "Drawn by AI from your photo")
    private let look = NSSegmentedControl(labels: ["Upload a photo", "Pick a breed"], trackingMode: .selectOne,
                                          target: nil, action: nil)
    private let photoButton = NSButton(title: "Choose Photo…", target: nil, action: nil)
    private let photoLabel = NSTextField(labelWithString: "")
    private let breedPop = NSPopUpButton(), colorPop = NSPopUpButton(), personalityPop = NSPopUpButton()
    private let blurb = NSTextField(wrappingLabelWithString: "")

    init(existing: SavedPet?) {
        self.existing = existing
        super.init()
        build()
        let isBreed = existing == nil || existing?["kind"] as? String == "breed"
        look.selectedSegment = isBreed ? 1 : 0
        if let b = existing?["breed"] as? String { select(breedPop, b) }
        fillColors(keep: existing?["color"] as? String)
        fillPersonalities(keep: (isBreed ? existing?["personality"] : existing?["preset"]) as? String ?? "")
    }

    var fromPhoto: Bool { look.selectedSegment == 0 }
    private var template: BreedTemplate { breedTemplate(selected(breedPop)) }

    var choice: PetChoice {
        PetChoice(name: String(name.stringValue.split(whereSeparator: { $0.isWhitespace })
                                .joined(separator: " ").prefix(Self.maxName)),
                  fromPhoto: fromPhoto, photoURL: photoURL,
                  breed: selected(breedPop) ?? breedTemplates[0].id, color: selected(colorPop) ?? "",
                  personality: selected(personalityPop) ?? "")
    }

    private func build() {
        let box = NSBox(frame: NSRect(x: 0, y: 0, width: 420, height: 110))
        box.boxType = .custom
        box.fillColor = NSColor(srgbRed: 0.18, green: 0.18, blue: 0.2, alpha: 1)
        box.borderWidth = 0
        box.cornerRadius = 8
        view.addSubview(box)
        preview.frame = NSRect(x: 10, y: 8, width: 400, height: 94)
        preview.imageScaling = .scaleNone
        previewNote.frame = NSRect(x: 0, y: 46, width: 420, height: 18)
        previewNote.alignment = .center
        previewNote.textColor = NSColor(white: 0.75, alpha: 1)
        view.addSubview(preview)
        view.addSubview(previewNote)

        var y: CGFloat = 122
        func row(_ label: String, _ control: NSView, height: CGFloat = 26) {
            let l = NSTextField(labelWithString: label)
            l.alignment = .right
            l.frame = NSRect(x: 0, y: y + 4, width: 84, height: 18)
            control.frame = NSRect(x: 92, y: y, width: 328, height: height)
            view.addSubview(l)
            view.addSubview(control)
            y += height + 6
        }
        name.placeholderString = "e.g. Biscuit"
        name.stringValue = existing?["name"] as? String ?? ""
        name.delegate = self
        row("Name", name, height: 24)
        look.target = self
        look.action = #selector(lookChanged)
        row("Look", look)

        let photoRow = NSView()
        photoButton.target = self
        photoButton.action = #selector(choosePhoto)
        photoButton.bezelStyle = .rounded
        photoButton.frame = NSRect(x: -6, y: -2, width: 140, height: 30)
        photoLabel.frame = NSRect(x: 140, y: 4, width: 188, height: 18)
        photoLabel.textColor = .secondaryLabelColor
        photoLabel.lineBreakMode = .byTruncatingMiddle
        photoRow.addSubview(photoButton)
        photoRow.addSubview(photoLabel)
        row("Photo", photoRow)

        for t in breedTemplates { addItem(breedPop, t.name, t.id) }
        breedPop.target = self
        breedPop.action = #selector(lookChanged)
        row("Breed", breedPop)
        colorPop.target = self
        colorPop.action = #selector(refresh)
        row("Color", colorPop)
        personalityPop.target = self
        personalityPop.action = #selector(refresh)
        row("Personality", personalityPop)
        blurb.frame = NSRect(x: 92, y: y, width: 328, height: 40)
        blurb.textColor = .secondaryLabelColor
        blurb.font = .systemFont(ofSize: NSFont.smallSystemFontSize)
        view.addSubview(blurb)
    }

    private func addItem(_ pop: NSPopUpButton, _ title: String, _ id: String) {
        pop.addItem(withTitle: title)
        pop.lastItem?.representedObject = id
    }

    private func selected(_ pop: NSPopUpButton) -> String? { pop.selectedItem?.representedObject as? String }

    @discardableResult private func select(_ pop: NSPopUpButton, _ id: String?) -> Bool {
        guard let i = pop.itemArray.firstIndex(where: { $0.representedObject as? String == id }) else { return false }
        pop.selectItem(at: i)
        return true
    }

    private func fillColors(keep: String? = nil) {
        let keep = keep ?? selected(colorPop)
        colorPop.removeAllItems()
        for c in template.colors { addItem(colorPop, c.name, c.id) }
        select(colorPop, keep)
    }

    private func fillPersonalities(keep: String? = nil) {
        let keep = keep ?? selected(personalityPop)
        personalityPop.removeAllItems()
        if fromPhoto { addItem(personalityPop, "Guess from the photo", "") }
        for p in personalities(for: fromPhoto ? "" : template.animal) { addItem(personalityPop, p.name, p.id) }
        if !select(personalityPop, keep) && !fromPhoto { select(personalityPop, template.defaultPersonality) }
    }

    @objc private func lookChanged() {
        fillColors()
        fillPersonalities()
        refresh()
    }

    func controlTextDidChange(_ obj: Notification) { refresh() }

    @objc private func choosePhoto() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.image]
        panel.message = "Pick a photo of your pet"
        if panel.runModal() == .OK, let url = panel.url {
            photoURL = url
            refresh()
        }
    }

    @objc func refresh() {
        let photo = fromPhoto
        photoButton.isEnabled = photo
        breedPop.isEnabled = !photo
        colorPop.isEnabled = !photo
        let keepsDrawing = photo && photoURL == nil && existing?["sprite"] != nil
        photoLabel.stringValue = photoURL?.lastPathComponent ?? (keepsDrawing ? "keeps the current drawing" : "")
        blurb.stringValue = personality(selected(personalityPop))?.text ?? "The AI picks a personality from the photo."
        var sprite: [String: Any]?
        if !photo {
            sprite = paintBreed(selected(breedPop), selected(colorPop))
        } else if keepsDrawing {
            sprite = existing?["sprite"] as? [String: Any]
        }
        showPreview(sprite)
        let hasName = !name.stringValue.trimmingCharacters(in: .whitespaces).isEmpty
        okButton?.isEnabled = hasName && (!photo || photoURL != nil || keepsDrawing)
    }

    private func showPreview(_ sprite: [String: Any]?) {
        guard let sprite, let pet = buildPet(id: "preview", name: "", sprite: sprite, dream: "z", dreamColor: .gray,
                                             thinking: "", keySaved: "", prompt: "") else {
            preview.image = nil
            previewNote.isHidden = false
            return
        }
        let px = max(2, min(4, (150 / CGFloat(pet.w)).rounded(.down)))
        let images = [pet.awake[0], pet.walk.first ?? pet.awake[0]].map { spriteImage($0, palette: pet.palette, px: px) }
        let gap: CGFloat = 24
        let size = NSSize(width: images.reduce(0) { $0 + $1.size.width } + gap,
                          height: images.map(\.size.height).max() ?? 1)
        preview.image = NSImage(size: size, flipped: false) { _ in
            var x: CGFloat = 0
            for image in images {
                image.draw(at: NSPoint(x: x, y: 0), from: .zero, operation: .sourceOver, fraction: 1)
                x += image.size.width + gap
            }
            return true
        }
        previewNote.isHidden = true
    }
}
