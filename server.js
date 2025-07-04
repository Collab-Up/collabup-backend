import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import nodemailer from "nodemailer";
dotenv.config();

const PORT = process.env.PORT || 5050;
const app = express();

// Allow only the Vercel frontend domain for CORS
app.use(cors({
  origin: 'https://frontend-two-omega-26.vercel.app',
  methods: ['GET', 'POST', 'OPTIONS'],
  credentials: true
}));
app.use(express.json());

app.post("/send-feedback", async (req, res) => {
  const { name, email, message } = req.body;

  if (!name || !email || !message) {
    return res.status(400).json({ error: "All fields are required." });
  }

  try {
    const transporter = nodemailer.createTransport({
      service: "gmail",
      auth: {
        user: process.env.MAIL_USER,
        pass: process.env.MAIL_PASS,
      },
    });

    const mailOptions = {
      from: `"${name}" <${email}>`,
      to: process.env.MAIL_RECEIVER,
      subject: `New Feedback from ${name}`,
      text: `
You have received a new feedback:

Name: ${name}
Email: ${email}
Message: ${message}
      `,
    };

    await transporter.sendMail(mailOptions);
    res.status(200).json({ success: true, message: "Email sent!" });
  } catch (error) {
    console.error("Mail error:", error);
    res.status(500).json({ error: "Failed to send email" });
  }
});

app.post("/api/send-email", async (req, res) => {
  const { to, subject, text, html } = req.body;
  if (!to || !subject || !text) {
    return res.status(400).json({ error: "To, subject, and text are required." });
  }
  try {
    const transporter = nodemailer.createTransport({
      service: "gmail",
      auth: {
        user: process.env.MAIL_USER,
        pass: process.env.MAIL_PASS,
      },
    });
    const mailOptions = {
      from: `CollabUp <${process.env.MAIL_USER}>`,
      to,
      subject,
      text,
      html: html || `<p>${text}</p>`
    };
    await transporter.sendMail(mailOptions);
    res.status(200).json({ success: true, message: "Email sent!" });
  } catch (error) {
    console.error("Mail error:", error);
    res.status(500).json({ error: "Failed to send email" });
  }
});
console.log("Loaded [server.js](http://_vscodecontentref_/0) and registered /api/send-email");
app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});
