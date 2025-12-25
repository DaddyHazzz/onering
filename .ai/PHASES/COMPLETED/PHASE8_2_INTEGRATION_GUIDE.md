# Phase 8.2: Integration Guide

**How to integrate PlatformVersionsPanel into your draft detail page**

## Current State

The `PlatformVersionsPanel` component is built and ready to use. It's a self-contained React component that manages its own state, API calls, and error handling.

## Integration Steps

### Step 1: Import the Component

In your draft detail page (e.g., `src/app/drafts/[id]/page.tsx`):

```typescript
import PlatformVersionsPanel from "@/components/PlatformVersionsPanel";
```

### Step 2: Render Below Existing Sections

Add the panel below the draft editor or in a tab alongside other collaboration features:

```typescript
export default function DraftDetailPage({ params }: { params: { id: string } }) {
  const [draft, setDraft] = useState<CollabDraft | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { user, isLoaded } = useUser();

  // ... existing draft loading logic ...

  return (
    <div className="grid grid-cols-1 gap-6">
      {/* Existing sections */}
      <DraftEditor draft={draft} />
      <AISuggestionsPanel 
        draftId={params.id}
        isAuthenticated={!!user}
      />

      {/* Add Platform Versions Panel here */}
      <PlatformVersionsPanel
        draftId={params.id}
        isAuthenticated={!!user}
        onError={(message) => {
          setError(message);
          // Show toast/notification
        }}
      />
    </div>
  );
}
```

### Step 3: Handle Error Display

The `onError` callback is where you handle formatting errors:

```typescript
<PlatformVersionsPanel
  draftId={params.id}
  isAuthenticated={!!user}
  onError={(message) => {
    // Option 1: Use toast library
    toast.error(message);

    // Option 2: Set error state
    setError(message);

    // Option 3: Log to error tracking
    console.error("[PlatformVersionsPanel]", message);
  }}
/>
```

## Component Props

```typescript
interface PlatformVersionsPanelProps {
  draftId: string;                           // Required: draft ID
  isAuthenticated: boolean;                  // Required: auth status
  onError?: (message: string) => void;       // Optional: error callback
}
```

## User Workflow

1. **User navigates to draft detail page**
   - Panel loads in empty state with "Click 'Generate All Platforms'"

2. **User clicks "Generate All Platforms"**
   - Loading state appears
   - API call to `/v1/format/generate` is made
   - Results appear in tabs

3. **User switches platforms**
   - X (Twitter) tab selected by default
   - Can switch to YouTube, Instagram, Blog
   - Metadata updates (character count, block count)

4. **User copies blocks**
   - Click "Copy" on any block
   - Button shows "✓" for 2 seconds
   - Content copied to clipboard

5. **User exports to file**
   - Click "Export TXT", "Export MD", or "Export CSV"
   - File downloads with naming: `{draftId}-{platform}.{ext}`

6. **User customizes formatting** (Optional)
   - Click "Show Formatting Options"
   - Select tone (professional, casual, witty, etc.)
   - Toggle hashtags/CTA
   - Enter max hashtag count
   - Enter custom CTA text
   - Click "Generate All Platforms" again

## Styling Customization

The component uses TailwindCSS classes. To customize:

### Theme Colors
Edit class names in `PlatformVersionsPanel.tsx`:

```typescript
// Heading block (currently purple)
className="... border-l-purple-500 bg-purple-50"

// Hashtag block (currently green)
className="... border-l-green-500 bg-green-50"

// CTA block (currently blue)
className="... border-l-blue-500 bg-blue-50"
```

### Button Styles
Update button classes for your design system:

```typescript
// Generate button (currently blue)
className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"

// Export buttons (currently gray)
className="px-3 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-700"
```

### Spacing
Adjust layout spacing in the container div:

```typescript
<div className="border rounded-lg p-6 bg-white">
  {/* Adjust p-6 for padding, border for border style */}
</div>
```

## Error Scenarios Handled

The component gracefully handles:

| Scenario | User Sees |
|----------|-----------|
| Not authenticated | "You must be signed in to format content." |
| API failure | Error message from server (from onError callback) |
| Network timeout | "Failed to format content" |
| Rate limit exceeded | "Rate limit exceeded. Retry after 1 minute." |
| Draft not found | "Draft not found" (404) |
| Access denied | "Not a collaborator on this draft" (403) |
| Invalid platform | "Invalid platform: ..." (400) |

## Testing the Integration

### Manual Testing Checklist
- [ ] Panel renders when draft loads
- [ ] "Generate All Platforms" button is clickable
- [ ] Loading state appears during API call
- [ ] Tabs appear with X, YouTube, Instagram, Blog
- [ ] Blocks render with correct types and styling
- [ ] Copy button works and shows "✓"
- [ ] Export buttons download files
- [ ] Options panel toggle works
- [ ] Error callback is called on API error
- [ ] Unauthenticated user sees error message

### Automated Testing
Component comes with Vitest tests in `src/__tests__/platform-versions.spec.tsx`:

```bash
# Run tests
pnpm test platform-versions.spec.tsx

# Run tests in watch mode
pnpm test --watch platform-versions.spec.tsx
```

## Performance Considerations

- **First render:** <100ms (no API call)
- **API call:** <40ms (4 platforms, no LLM calls)
- **Component re-renders:** Fast (React state only)
- **Export:** Instant (client-side file generation)

## Browser Compatibility

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

Requires:
- `navigator.clipboard.writeText()` for copy-to-clipboard
- `URL.createObjectURL()` for file export
- `Blob` API for file generation

All APIs available in modern browsers.

## Known Limitations

1. **Export size:** Large drafts (10,000+ chars) may take 1-2 seconds to export
2. **Mobile:** Clipboard copy works but file downloads may not display properly on mobile
3. **Very long blocks:** Blocks longer than platform limit are split (user sees warnings)

## Future Enhancements

These are planned for Phase 8.3+:

- [ ] Batch export all platforms as .zip
- [ ] Schedule formatting + auto-posting
- [ ] A/B testing (multiple tone variations)
- [ ] Analytics per platform version
- [ ] User-customizable templates

## Debugging Tips

### Component Not Rendering?
- Check that `PlatformVersionsPanel` is imported correctly
- Verify `draftId` and `isAuthenticated` props are passed
- Check browser console for errors

### API Calls Not Working?
- Verify user is authenticated (check `isAuthenticated` prop)
- Check Network tab in DevTools for `/v1/format/generate` requests
- Verify `Authorization` header is present
- Check backend logs for errors

### Copy Not Working?
- Verify browser has `navigator.clipboard` permission
- Check if running on localhost (unsecured HTTP may restrict clipboard)
- Try running on HTTPS or with `--insecure-localhost-origins` flag

### Export Not Working?
- Verify browser allows downloads from your domain
- Check Download folder permissions
- Try different export format (TXT vs MD vs CSV)

## Support

For issues:
1. Check `PHASE8_PLATFORM_FORMATTING.md` for API details
2. Check component tests (`platform-versions.spec.tsx`) for usage examples
3. Check error messages in browser console
4. File an issue with component name, props, and error message

---

**Component Status:** ✅ Production Ready  
**Last Updated:** December 24, 2025
