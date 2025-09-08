// static/media/media.js
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("local-form");
  const result = document.getElementById("result");
  const btnPresign = document.getElementById("btn-presign");
  const presignBox = document.getElementById("presign-box");
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(form);
      const res = await fetch("/api/media/upload", { method: "POST", body: fd });
      const data = await res.json();
      result.textContent = res.ok ? `Uploaded: id ${data.id}` : (data.error || "Upload failed");
    });
  }
  if (btnPresign) {
    btnPresign.addEventListener("click", async () => {
      const res = await fetch("/api/media/presign", { method: "POST" });
      const data = await res.json();
      presignBox.textContent = JSON.stringify(data, null, 2);
    });
  }
});
