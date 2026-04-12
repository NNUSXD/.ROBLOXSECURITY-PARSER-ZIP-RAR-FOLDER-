using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Windows.Forms;
using ICSharpCode.SharpZipLib.Tar;
using ICSharpCode.SharpZipLib.GZip;
using ICSharpCode.SharpZipLib.BZip2;
using Ionic.Zip;
using SevenZip;

namespace DreadParser
{
    public partial class MainForm : Form
    {
        private List<string> foundCookies = new List<string>();
        private HashSet<string> seenCookies = new HashSet<string>();
        private string safeFilesPath = "";
        private string resultFilePath = "";
        private Timer gradientTimer;
        private float gradientAngle = 0f;
        
        private const string WARNING_SIGNATURE = "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_";
        private static readonly HashSet<string> DANGEROUS_EXTENSIONS = new HashSet<string>
        {
            ".exe", ".dll", ".bat", ".cmd", ".sh", ".ps1", ".vbs", ".js", ".wsf",
            ".jar", ".class", ".py", ".pyc", ".scr", ".lnk", ".reg", ".msi", ".com", ".hta", ".pif", ".cpl"
        };

        public MainForm()
        {
            InitializeComponent();
            SetupGradientAnimation();
            ApplyNeonStyle();
        }

        private void SetupGradientAnimation()
        {
            gradientTimer = new Timer();
            gradientTimer.Interval = 50;
            gradientTimer.Tick += (s, e) =>
            {
                gradientAngle += 2f;
                if (gradientAngle >= 360f) gradientAngle = 0f;
                Invalidate();
            };
            gradientTimer.Start();
        }

        private void ApplyNeonStyle()
        {
            BackColor = Color.FromArgb(10, 10, 20);
            Font = new Font("Segoe UI", 10F, FontStyle.Regular);
            
            // Main panel styling
            mainPanel.BackColor = Color.FromArgb(15, 15, 30);
            mainPanel.Dock = DockStyle.Fill;
            mainPanel.Padding = new Padding(20);
            
            // Title label
            titleLabel.Font = new Font("Segoe UI", 18F, FontStyle.Bold);
            titleLabel.ForeColor = Color.Lime;
            titleLabel.TextAlign = ContentAlignment.MiddleCenter;
            titleLabel.Dock = DockStyle.Top;
            titleLabel.Height = 50;
            
            // Status label
            statusLabel.Font = new Font("Consolas", 9F, FontStyle.Regular);
            statusLabel.ForeColor = Color.Yellow;
            statusLabel.TextAlign = ContentAlignment.MiddleCenter;
            statusLabel.Dock = DockStyle.Bottom;
            statusLabel.Height = 30;
            
            // Progress bar custom styling
            progressBar.Dock = DockStyle.Bottom;
            progressBar.Height = 8;
            progressBar.Style = ProgressBarStyle.Continuous;
            
            // Output textbox
            outputTextBox.BackColor = Color.FromArgb(5, 5, 15);
            outputTextBox.ForeColor = Color.Lime;
            outputTextBox.Font = new Font("Consolas", 9F, FontStyle.Regular);
            outputTextBox.BorderStyle = BorderStyle.None;
            outputTextBox.Dock = DockStyle.Fill;
            outputTextBox.ReadOnly = true;
            
            // Buttons styling
            StyleButton(selectArchiveBtn, Color.Lime, "📂 Выбрать Архив");
            StyleButton(openFolderBtn, Color.Yellow, "📁 Пути");
            StyleButton(exportBtn, Color.Orange, "📤 Экспорт");
            StyleButton(clearBtn, Color.Red, "🗑️ Очистить");
            
            // Password textbox
            passwordTextBox.BackColor = Color.FromArgb(20, 20, 40);
            passwordTextBox.ForeColor = Color.Lime;
            passwordTextBox.Font = new Font("Consolas", 10F, FontStyle.Regular);
            passwordTextBox.BorderStyle = BorderStyle.FixedSingle;
            passwordTextBox.PasswordChar = '●';
        }

        private void StyleButton(Button btn, Color baseColor, string text)
        {
            btn.FlatStyle = FlatStyle.Flat;
            btn.FlatAppearance.BorderSize = 0;
            btn.BackColor = Color.FromArgb(20, 20, 40);
            btn.ForeColor = baseColor;
            btn.Font = new Font("Segoe UI", 11F, FontStyle.Bold);
            btn.Text = text;
            btn.Cursor = Cursors.Hand;
            btn.FlatAppearance.MouseOverBackColor = Color.FromArgb(30, 30, 60);
            btn.FlatAppearance.MouseDownBackColor = Color.FromArgb(40, 40, 80);
            
            btn.Paint += (s, e) =>
            {
                var g = e.Graphics;
                using (var brush = new SolidBrush(Color.FromArgb(50, baseColor)))
                {
                    g.FillRectangle(brush, btn.ClientRectangle);
                }
                using (var pen = new Pen(baseColor, 2))
                {
                    var rect = btn.ClientRectangle;
                    rect.Inflate(-2, -2);
                    g.DrawRectangle(pen, rect);
                }
                
                // Glow effect
                using (var path = new GraphicsPath())
                {
                    path.AddRectangle(btn.ClientRectangle);
                    using (var blur = new BlurEffect(10))
                    {
                        // Note: Actual glow requires more complex implementation
                    }
                }
            };
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            base.OnPaint(e);
            
            // Animated gradient background
            using (var brush = new LinearGradientBrush(
                ClientRectangle,
                Color.FromArgb(10, 10, 20),
                Color.FromArgb(20, 30, 20),
                gradientAngle))
            {
                e.Graphics.FillRectangle(brush, ClientRectangle);
            }
        }

        private void InitializeComponent()
        {
            this.mainPanel = new System.Windows.Forms.Panel();
            this.titleLabel = new System.Windows.Forms.Label();
            this.selectArchiveBtn = new System.Windows.Forms.Button();
            this.passwordLabel = new System.Windows.Forms.Label();
            this.passwordTextBox = new System.Windows.Forms.TextBox();
            this.progressBar = new System.Windows.Forms.ProgressBar();
            this.statusLabel = new System.Windows.Forms.Label();
            this.outputTextBox = new System.Windows.Forms.RichTextBox();
            this.buttonPanel = new System.Windows.Forms.FlowLayoutPanel();
            this.openFolderBtn = new System.Windows.Forms.Button();
            this.exportBtn = new System.Windows.Forms.Button();
            this.clearBtn = new System.Windows.Forms.Button();
            
            SuspendLayout();
            
            // mainPanel
            mainPanel.Controls.Add(titleLabel);
            mainPanel.Controls.Add(outputTextBox);
            mainPanel.Controls.Add(buttonPanel);
            mainPanel.Controls.Add(passwordTextBox);
            mainPanel.Controls.Add(passwordLabel);
            mainPanel.Controls.Add(selectArchiveBtn);
            mainPanel.Controls.Add(progressBar);
            mainPanel.Controls.Add(statusLabel);
            
            // titleLabel
            titleLabel.Name = "titleLabel";
            titleLabel.Text = "⚡ DREAD PARSER ⚡\n🛡️ Максимальная Полнота Поиска";
            
            // selectArchiveBtn
            selectArchiveBtn.Location = new Point(200, 70);
            selectArchiveBtn.Size = new Size(300, 45);
            selectArchiveBtn.Click += SelectArchiveBtn_Click;
            
            // passwordLabel
            passwordLabel.AutoSize = true;
            passwordLabel.Location = new Point(250, 125);
            passwordLabel.Text = "🔑 Пароль от архива:";
            passwordLabel.ForeColor = Color.Yellow;
            
            // passwordTextBox
            passwordTextBox.Location = new Point(220, 150);
            passwordTextBox.Size = new Size(260, 25);
            
            // progressBar
            progressBar.Name = "progressBar";
            
            // statusLabel
            statusLabel.Name = "statusLabel";
            statusLabel.Text = "⏳ Ожидание...";
            
            // outputTextBox
            outputTextBox.Name = "outputTextBox";
            
            // buttonPanel
            buttonPanel.Dock = DockStyle.Bottom;
            buttonPanel.Height = 50;
            buttonPanel.FlowDirection = FlowDirection.LeftToRight;
            buttonPanel.WrapContents = true;
            buttonPanel.Controls.Add(openFolderBtn);
            buttonPanel.Controls.Add(exportBtn);
            buttonPanel.Controls.Add(clearBtn);
            
            openFolderBtn.Size = new Size(130, 35);
            openFolderBtn.Click += OpenFolderBtn_Click;
            
            exportBtn.Size = new Size(130, 35);
            exportBtn.Click += ExportBtn_Click;
            
            clearBtn.Size = new Size(130, 35);
            clearBtn.Click += ClearBtn_Click;
            
            // MainForm
            AutoScaleDimensions = new SizeF(7F, 15F);
            AutoScaleMode = AutoScaleMode.Font;
            ClientSize = new Size(700, 600);
            Controls.Add(mainPanel);
            FormBorderStyle = FormBorderStyle.FixedSingle;
            MaximizeBox = false;
            Name = "MainForm";
            StartPosition = FormStartPosition.CenterScreen;
            Text = "⚡ DREAD PARSER v1.0";
            
            ResumeLayout(false);
            PerformLayout();
        }

        private Panel mainPanel;
        private Label titleLabel;
        private Button selectArchiveBtn;
        private Label passwordLabel;
        private TextBox passwordTextBox;
        private ProgressBar progressBar;
        private Label statusLabel;
        private RichTextBox outputTextBox;
        private FlowLayoutPanel buttonPanel;
        private Button openFolderBtn;
        private Button exportBtn;
        private Button clearBtn;

        private async void SelectArchiveBtn_Click(object sender, EventArgs e)
        {
            using (var dialog = new OpenFileDialog())
            {
                dialog.Title = "Выберите Архив (ZIP/RAR/7Z/TAR/GZ)";
                dialog.Filter = "Архивы|*.zip;*.rar;*.7z;*.tar;*.gz;*.bz2|Все файлы|*.*";
                
                if (dialog.ShowDialog() == DialogResult.OK)
                {
                    await ProcessArchiveAsync(dialog.FileName);
                }
            }
        }

        private async Task ProcessArchiveAsync(string archivePath)
        {
            try
            {
                ResetUI();
                UpdateStatus("🧹 Очистка...", 5);
                
                string scriptDir = Path.GetDirectoryName(Application.ExecutablePath);
                string tempFolder = Path.Combine(scriptDir, "__temp_secure_extract");
                safeFilesPath = Path.Combine(scriptDir, "verified_txt_files");
                resultFilePath = Path.Combine(scriptDir, "roblox_cookies.txt");
                
                // Cleanup
                SafeRemoveDirectory(tempFolder);
                SafeRemoveDirectory(safeFilesPath);
                Directory.CreateDirectory(tempFolder);
                Directory.CreateDirectory(safeFilesPath);
                
                UpdateStatus("📦 Извлечение...", 10);
                
                // Extract archive (single-threaded)
                bool extractedSuccessfully = await Task.Run(() => ExtractArchive(archivePath, tempFolder));
                
                if (!extractedSuccessfully)
                    throw new Exception("Не удалось извлечь архив.");
                
                // Collect all files
                var allFiles = new List<string>();
                foreach (var file in Directory.GetFiles(tempFolder, "*.*", SearchOption.AllDirectories))
                {
                    if (IsSafePath(tempFolder, file) && !new FileInfo(file).Attributes.HasFlag(FileAttributes.ReparsePoint))
                        allFiles.Add(file);
                }
                
                if (allFiles.Count == 0)
                    throw new Exception("Архив пуст или не содержит файлов.");
                
                UpdateStatus("🔍 Поиск кук...", 20);
                
                int validFilesCount = 0;
                int skippedCookiesCount = 0;
                
                for (int idx = 0; idx < allFiles.Count; idx++)
                {
                    string filePath = allFiles[idx];
                    
                    try
                    {
                        if (!IsSafeTextFile(filePath))
                        {
                            try { File.Delete(filePath); } catch { }
                            continue;
                        }
                        
                        var cookies = ParseFileContent(filePath);
                        
                        foreach (var cookie in cookies)
                        {
                            if (AddCookieUnique(cookie))
                                AppendOutput($"[✓] {Path.GetFileName(filePath)}: +1 кука");
                        }
                        
                        // Check for potential skips
                        if (cookies.Count == 0)
                        {
                            try
                            {
                                string content = File.ReadAllText(filePath, Encoding.UTF8);
                                if (content.Contains(".ROBLOSECURITY") || content.Contains(WARNING_SIGNATURE))
                                    skippedCookiesCount++;
                            } catch { }
                        }
                        
                        // Move processed file
                        string filename = Path.GetFileName(filePath);
                        string targetPath = Path.Combine(safeFilesPath, filename);
                        if (File.Exists(targetPath))
                        {
                            string name = Path.GetFileNameWithoutExtension(filename);
                            string ext = Path.GetExtension(filename);
                            int counter = 1;
                            while (File.Exists(targetPath))
                            {
                                targetPath = Path.Combine(safeFilesPath, $"{name}_{counter}{ext}");
                                counter++;
                            }
                        }
                        File.Move(filePath, targetPath);
                        validFilesCount++;
                    }
                    catch (Exception ex)
                    {
                        AppendOutput($"⚠️ Ошибка файла {filePath}: {ex.Message}");
                    }
                    
                    int progress = 20 + (80 * (idx + 1) / allFiles.Count);
                    UpdateStatus($"⚙️ {idx + 1}/{allFiles.Count} | Файлов: {validFilesCount}", Math.Min(progress, 99));
                }
                
                // Cleanup temp folder
                SafeRemoveDirectory(tempFolder);
                UpdateStatus("✅ Готово!", 100);
                
                // Save results
                if (foundCookies.Count > 0)
                {
                    StringBuilder sb = new StringBuilder();
                    sb.AppendLine($"Всего кук: {foundCookies.Count}");
                    sb.AppendLine($"Проверено файлов: {validFilesCount}");
                    sb.AppendLine($"Потенциально пропущено: {skippedCookiesCount}");
                    sb.AppendLine(new string('=', 50));
                    sb.AppendLine();
                    
                    for (int i = 0; i < foundCookies.Count; i++)
                        sb.AppendLine($"{i + 1}. {foundCookies[i]}");
                    
                    File.WriteAllText(resultFilePath, sb.ToString(), Encoding.UTF8);
                    
                    string resultMsg = $"✅ Обработано файлов: {validFilesCount}\n🍪 Найдено уникальных кук: {foundCookies.Count}";
                    AppendOutput($"\n{new string('=', 40)}\n{resultMsg}");
                    
                    EnableResultButtons();
                    MessageBox.Show($"{resultMsg}\n\n✅ Файл создан:\n{resultFilePath}", "Успех", 
                        MessageBoxButtons.OK, MessageBoxIcon.Information);
                }
                else
                {
                    MessageBox.Show("Куки не найдены в обработанных файлах.", "Готово", 
                        MessageBoxButtons.OK, MessageBoxIcon.Information);
                }
            }
            catch (Exception ex)
            {
                UpdateStatus("❌ Ошибка!", 0);
                MessageBox.Show($"Критическая ошибка: {ex.Message}", "Ошибка", 
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
                AppendOutput($"❌ {ex.Message}");
            }
        }

        private bool ExtractArchive(string archivePath, string outputFolder)
        {
            string fileExt = Path.GetExtension(archivePath).ToLowerInvariant();
            string password = passwordTextBox.Text.Trim();
            
            try
            {
                switch (fileExt)
                {
                    case ".zip":
                        using (var zip = ZipFile.Read(archivePath))
                        {
                            if (!string.IsNullOrEmpty(password))
                                zip.Password = password;
                            zip.ExtractAll(outputFolder, ExtractExistingFileAction.OverwriteSilently);
                        }
                        AppendOutput("✅ Извлечено через DotNetZip.");
                        return true;
                        
                    case ".rar":
                        SevenZipExtractor.SetLibraryPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "7z.dll"));
                        using (var extractor = new SevenZipExtractor(archivePath))
                        {
                            if (!string.IsNullOrEmpty(password))
                                extractor.Password = password;
                            extractor.ExtractArchive(outputFolder);
                        }
                        AppendOutput("✅ Извлечено через 7-Zip (RAR).");
                        return true;
                        
                    case ".7z":
                        SevenZipExtractor.SetLibraryPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "7z.dll"));
                        using (var extractor = new SevenZipExtractor(archivePath))
                        {
                            if (!string.IsNullOrEmpty(password))
                                extractor.Password = password;
                            extractor.ExtractArchive(outputFolder);
                        }
                        AppendOutput("✅ Извлечено через 7-Zip (7Z).");
                        return true;
                        
                    case ".tar":
                        using (Stream inStream = File.OpenRead(archivePath))
                        using (var tarArchive = TarArchive.CreateInputTarArchive(inStream))
                            tarArchive.ExtractContents(outputFolder);
                        AppendOutput("✅ Извлечено через SharpZipLib (TAR).");
                        return true;
                        
                    case ".gz":
                        using (Stream inStream = File.OpenRead(archivePath))
                        using (Stream outStream = File.Create(Path.Combine(outputFolder, Path.GetFileNameWithoutExtension(archivePath))))
                        using (var gzip = new GZipInputStream(inStream))
                            gzip.CopyTo(outStream);
                        AppendOutput("✅ Извлечено через SharpZipLib (GZ).");
                        return true;
                        
                    case ".bz2":
                        using (Stream inStream = File.OpenRead(archivePath))
                        using (Stream outStream = File.Create(Path.Combine(outputFolder, Path.GetFileNameWithoutExtension(archivePath))))
                        using (var bzip = new BZip2InputStream(inStream))
                            bzip.CopyTo(outStream);
                        AppendOutput("✅ Извлечено через SharpZipLib (BZ2).");
                        return true;
                        
                    default:
                        AppendOutput($"⚠️ Неподдерживаемый формат: {fileExt}");
                        return false;
                }
            }
            catch (Exception ex)
            {
                string errorStr = ex.Message.ToLowerInvariant();
                if (errorStr.Contains("crc") || errorStr.Contains("corrupt") || errorStr.Contains("damaged"))
                    throw new Exception("❌ ОШИБКА: Архив повреждён (CRC Error).\nПопробуйте скачать его заново.");
                else if (errorStr.Contains("password") || errorStr.Contains("encrypted") || errorStr.Contains("wrong"))
                    throw new Exception("❌ ОШИБКА: Неверный пароль или архив зашифрован.");
                else
                    throw new Exception($"❌ Ошибка извлечения: {ex.Message}");
            }
        }

        private List<string> ParseFileContent(string filePath)
        {
            try
            {
                string content = File.ReadAllText(filePath, Encoding.UTF8);
                return FindRoblosecurityCookies(content);
            }
            catch
            {
                try
                {
                    byte[] bytes = File.ReadAllBytes(filePath);
                    string content = Encoding.UTF8.GetString(bytes);
                    return FindRoblosecurityCookies(content);
                }
                catch
                {
                    return new List<string>();
                }
            }
        }

        private List<string> FindRoblosecurityCookies(string content)
        {
            var cookies = new List<string>();
            var foundTokens = new HashSet<string>();
            
            // Clean content
            string contentClean = content.Replace("\\n", "\n").Replace("\\t", "\t").Replace("\\\"", "\"");
            
            // Pattern 1: WARNING_SIGNATURE
            int searchStart = 0;
            while (true)
            {
                int sigPos = contentClean.IndexOf(WARNING_SIGNATURE, searchStart);
                if (sigPos == -1) break;
                
                string after = contentClean.Substring(sigPos + WARNING_SIGNATURE.Length).TrimStart(new char[] { '=', ':', ' ', '\t', '\n', '\r', '"', '\'' });
                if (after.Length > 0 && char.IsLetterOrDigit(after[0]))
                {
                    string token = ExtractValidToken(after);
                    if (!string.IsNullOrEmpty(token) && !foundTokens.Contains(token))
                    {
                        foundTokens.Add(token);
                        cookies.Add(WARNING_SIGNATURE + token);
                    }
                }
                searchStart = sigPos + 1;
            }
            
            // Pattern 2: JSON and JS patterns
            string[] jsonPatterns = new string[]
            {
                @"""ROBLOSECURITY""\s*:\s*""([A-Za-z0-9+/=_|-]{50,})""",
                @"\\""ROBLOSECURITY\\"\s*:\s*\\""([A-Za-z0-9+/=_|-]{50,})\\"" ",
                @"['""]?\.ROBLOSECURITY['""]?\s*[:=]\s*['""]?([A-Za-z0-9+/=_|-]{50,})['""]?",
                @"ROBLOSECURITY['""]?\s*[:=]\s*['""]?([A-Za-z0-9+/=_|-]{50,})",
                @"%2EROBLOSECURITY(?:%3D|=)([A-Za-z0-9%+/=_|-]{50,})"
            };
            
            foreach (string pattern in jsonPatterns)
            {
                var matches = Regex.Matches(contentClean, pattern, RegexOptions.IgnoreCase);
                foreach (Match match in matches)
                {
                    string token = match.Groups[1].Value.Trim('"', '\'', '\\');
                    if (token.Contains("%2") || token.Contains("%3"))
                    {
                        try { token = Uri.UnescapeDataString(token); } catch { }
                    }
                    if (IsValidRobloxToken(token) && !foundTokens.Contains(token))
                    {
                        foundTokens.Add(token);
                        cookies.Add(WARNING_SIGNATURE + token);
                    }
                }
            }
            
            // Pattern 3: Cookie header style
            string[] cookiePatterns = new string[]
            {
                @"\.ROBLOSECURITY\s*=\s*([A-Za-z0-9+/=_|-]{50,})(?:;|$|\s|&)",
                @"cookie[^:]*:\s*[^;]*\.ROBLOSECURITY=([A-Za-z0-9+/=_|-]{50,})(?:;|$)"
            };
            
            foreach (string pattern in cookiePatterns)
            {
                var matches = Regex.Matches(contentClean, pattern, RegexOptions.IgnoreCase);
                foreach (Match match in matches)
                {
                    string token = match.Groups[1].Value.TrimEnd(';').Trim();
                    if (IsValidRobloxToken(token) && !foundTokens.Contains(token))
                    {
                        foundTokens.Add(token);
                        cookies.Add(WARNING_SIGNATURE + token);
                    }
                }
            }
            
            // Pattern 4: Raw search
            searchStart = 0;
            while (true)
            {
                int pos = contentClean.ToLower().IndexOf(".roblosecurity", searchStart);
                if (pos == -1) break;
                
                int startIdx = pos + ".ROBLOSECURITY".Length;
                int length = Math.Min(1500, contentClean.Length - startIdx);
                string after = contentClean.Substring(startIdx, length);
                after = Regex.Replace(after, @"^[=: \t\n\r""'|,;]+", "");
                
                if (after.Length > 0 && char.IsLetterOrDigit(after[0]))
                {
                    string token = ExtractValidToken(after);
                    if (!string.IsNullOrEmpty(token) && IsValidRobloxToken(token) && !foundTokens.Contains(token))
                    {
                        foundTokens.Add(token);
                        cookies.Add(WARNING_SIGNATURE + token);
                    }
                }
                searchStart = pos + 1;
            }
            
            // Pattern 5: Base64-like strings near keywords
            string[] keywords = new string[] { ".ROBLOSECURITY", "roblosecurity", "ROBLOSECURITY" };
            foreach (string keyword in keywords)
            {
                int idx = 0;
                while (idx < contentClean.Length)
                {
                    int pos = contentClean.IndexOf(keyword, idx);
                    if (pos == -1) break;
                    
                    int start = Math.Max(0, pos - 200);
                    int end = Math.Min(contentClean.Length, pos + 200 + 1000);
                    string context = contentClean.Substring(start, end - start);
                    
                    var base64Matches = Regex.Matches(context, @"([A-Za-z0-9+/=_|-]{50,})");
                    foreach (Match match in base64Matches)
                    {
                        string candidate = match.Groups[1].Value.Trim('"', '\'', ' ', '\t', '\n', '\r');
                        if (IsValidRobloxToken(candidate) && !foundTokens.Contains(candidate))
                        {
                            foundTokens.Add(candidate);
                            cookies.Add(WARNING_SIGNATURE + candidate);
                        }
                    }
                    idx = pos + 1;
                }
            }
            
            return cookies;
        }

        private string ExtractValidToken(string cookiePart)
        {
            if (string.IsNullOrEmpty(cookiePart)) return null;
            
            cookiePart = cookiePart.TrimStart(new char[] { '=', ':', ' ', '\t', '\n', '\r', '"', '\'', '|' });
            
            StringBuilder validToken = new StringBuilder();
            HashSet<char> stopChars = new HashSet<char> { ' ', '\t', '\n', '\r', ';', '"', '\'', '}', ']', '>', ',', '<', ')', '(', '\\', '&', '?', '#' };
            
            foreach (char c in cookiePart)
            {
                if (stopChars.Contains(c)) break;
                validToken.Append(c);
            }
            
            string token = validToken.ToString().Trim('"', '\'', ' ', '\t', '\n', '\r');
            
            if (IsValidRobloxToken(token)) return token;
            return null;
        }

        private bool IsValidRobloxToken(string token)
        {
            if (string.IsNullOrEmpty(token)) return false;
            
            token = token.Trim('"', '\'', ' ', '\t', '\n', '\r');
            
            if (token.Length < 50 || token.Length > 1000) return false;
            
            return Regex.IsMatch(token, @"^[A-Za-z0-9+/=_|-]+$");
        }

        private bool AddCookieUnique(string cookie)
        {
            string normalized = NormalizeCookie(cookie);
            
            if (seenCookies.Contains(normalized)) return false;
            
            seenCookies.Add(normalized);
            foundCookies.Add(cookie);
            
            return true;
        }

        private string NormalizeCookie(string cookie)
        {
            if (cookie.StartsWith(WARNING_SIGNATURE))
                return cookie.Substring(WARNING_SIGNATURE.Length).Trim();
            return cookie.Trim();
        }

        private bool IsSafeTextFile(string filePath)
        {
            if (!File.Exists(filePath) || new FileInfo(filePath).Attributes.HasFlag(FileAttributes.ReparsePoint))
                return false;
            
            string filename = Path.GetFileName(filePath).ToLowerInvariant();
            string ext = Path.GetExtension(filename);
            
            HashSet<string> allowedExts = new HashSet<string> { ".txt", ".log", ".json", ".js", ".html", ".xml", ".csv", ".cfg", ".ini", ".conf" };
            
            if (!allowedExts.Contains(ext))
                return false;
            
            foreach (string dangerousExt in DANGEROUS_EXTENSIONS)
            {
                if (filename.EndsWith(dangerousExt)) return false;
            }
            
            return true;
        }

        private bool IsSafePath(string basePath, string targetPath)
        {
            try
            {
                string baseResolved = Path.GetFullPath(basePath);
                string targetResolved = Path.GetFullPath(targetPath);
                return targetResolved.StartsWith(baseResolved, StringComparison.OrdinalIgnoreCase);
            }
            catch
            {
                return false;
            }
        }

        private void SafeRemoveDirectory(string path)
        {
            try
            {
                if (Directory.Exists(path))
                    Directory.Delete(path, true);
            }
            catch { }
        }

        private void ResetUI()
        {
            outputTextBox.Clear();
            progressBar.Value = 0;
            statusLabel.Text = "🚀 Запуск...";
            openFolderBtn.Enabled = false;
            exportBtn.Enabled = false;
            foundCookies.Clear();
            seenCookies.Clear();
            Application.DoEvents();
        }

        private void UpdateStatus(string text, int progress)
        {
            statusLabel.Text = text;
            progressBar.Value = progress;
            Application.DoEvents();
        }

        private void AppendOutput(string text)
        {
            outputTextBox.AppendText(text + Environment.NewLine);
            outputTextBox.ScrollToCaret();
            Application.DoEvents();
        }

        private void EnableResultButtons()
        {
            openFolderBtn.Enabled = true;
            exportBtn.Enabled = true;
        }

        private void OpenFolderBtn_Click(object sender, EventArgs e)
        {
            if (!string.IsNullOrEmpty(safeFilesPath) && Directory.Exists(safeFilesPath))
            {
                string message = $"📁 Проверенные файлы:\n{safeFilesPath}\n\n💾 Результаты:\n{resultFilePath}";
                MessageBox.Show(message, "Результаты", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
            else
            {
                MessageBox.Show("Не удалось определить путь.", "Ошибка", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void ExportBtn_Click(object sender, EventArgs e)
        {
            if (foundCookies.Count > 0)
            {
                using (var form = new Form())
                {
                    form.Text = "Экспорт Кук";
                    form.Size = new Size(400, 300);
                    form.StartPosition = FormStartPosition.CenterParent;
                    form.FormBorderStyle = FormBorderStyle.FixedDialog;
                    form.MaximizeBox = false;
                    
                    var textBox = new TextBox();
                    textBox.Multiline = true;
                    textBox.ScrollBars = ScrollBars.Vertical;
                    textBox.Dock = DockStyle.Fill;
                    textBox.ReadOnly = true;
                    textBox.BackColor = Color.FromArgb(5, 5, 15);
                    textBox.ForeColor = Color.Lime;
                    textBox.Font = new Font("Consolas", 9F);
                    
                    foreach (string cookie in foundCookies)
                        textBox.AppendText(cookie + Environment.NewLine);
                    
                    form.Controls.Add(textBox);
                    form.ShowDialog(this);
                }
            }
            else
            {
                MessageBox.Show("Куки не найдены.", "Инфо", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
        }

        private void ClearBtn_Click(object sender, EventArgs e)
        {
            if (foundCookies.Count > 0)
            {
                if (MessageBox.Show("Очистить все куки?", "Подтверждение", 
                    MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
                {
                    foundCookies.Clear();
                    seenCookies.Clear();
                    outputTextBox.Clear();
                    statusLabel.Text = "🗑️ Очищено";
                    openFolderBtn.Enabled = false;
                    exportBtn.Enabled = false;
                }
            }
        }
    }

    static class Program
    {
        [STAThread]
        static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new MainForm());
        }
    }
}
