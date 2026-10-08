首张电箱CLOSED实际复制/完整提示词保存/尺寸/透明像素/SHA读取命令，exit 0。

$target='D:/深度能力/output/art-concepts/asset-pack/room2'; New-Item -ItemType Directory -Force -Path $target | Out-Null
Copy-Item -LiteralPath 'C:\Users\liyh\.codex\generated_images\01a11c34-55d8-70d1-9b70-804744d0b7f7\exec-809327e6-e0f9-48a9-a0d0-e83e51052ab7.png' -Destination "$target/r2_powerbox_closed.png"
[System.IO.File]::WriteAllText("$target/r2_powerbox_closed-prompt.md",'Use case: stylized-concept. Asset type: separate transparent game object r2_powerbox_closed. Primary request: reproduce ONLY the wall electrical cabinet from Image 2, isolated, completely closed. Image 1 style reference; Image 2 object reference. Tall rectangular gray blue painted metal box, dark border, hinges left, recessed handle right, 4 corner screw heads. Door CLOSED conceals all interior, no fuse visible, no wiring visible, no light on. Front facing slight top/right depth, all edges intact, centered with small margins, transparent background, no wall, no tabletop. Soft painterly hand-drawn gouache game illustration, muted slate blue green oxidized painted metal, warm brown wood, parchment cream, clear mechanical structure, fine gently irregular outlines and subtle brush texture, matte soft diffuse light, faithful to references. No photorealism, no hard glossy reflections, no busy dirt, no people, no watermark, no extra puzzle answers.',[System.Text.UTF8Encoding]::new($false))
Add-Type -AssemblyName System.Drawing
$b=[System.Drawing.Bitmap]::new("$target/r2_powerbox_closed.png")
$alpha=$false
for($x=0;$x -lt $b.Width;$x+=16){for($y=0;$y -lt $b.Height;$y+=16){if($b.GetPixel($x,$y).A -lt 255){$alpha=$true;break}};if($alpha){break}}
@{name='r2_powerbox_closed';width=$b.Width;height=$b.Height;alpha=$alpha;sha256=(Get-FileHash -LiteralPath "$target/r2_powerbox_closed.png" -Algorithm SHA256).Hash.ToLower()} | ConvertTo-Json -Compress
$b.Dispose()
