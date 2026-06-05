# assets

Put a screen recording of the live flow here so the main README can show it.

## How to add the demo GIF

1. **Record** the conversation in Claude Desktop (fridge → recipe → save to
   Thermomix). On macOS: `Cmd-Shift-5` → record a region → stop. You'll get a
   `.mov`.
2. **Convert to GIF** (keeps the file small and inline-playable on GitHub):

   ```bash
   # with ffmpeg + gifski (brew install ffmpeg gifski)
   ffmpeg -i recording.mov -vf "fps=12,scale=900:-1" -f yuv4mpegpipe - \
     | gifski -o demo.gif --quality 80 -
   ```

   Or simplest: drop the `.mov`/`.mp4` straight into a GitHub issue/PR comment
   and GitHub will host it — paste that URL into the README instead.
3. **Save it here** as `assets/demo.gif`.
4. **Uncomment** the image line in the top-level `README.md` (in the Demo
   section):

   ```markdown
   ![Fridge to Thermomix](assets/demo.gif)
   ```

A short clip (15–30s) showing the three tools in action is plenty. A photo of
the recipe appearing on the Thermomix is a nice bonus — save it as
`assets/thermomix.jpg` and reference it the same way.
