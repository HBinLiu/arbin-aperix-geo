import { ArrowRight } from "lucide-react";
import { useState, type SubmitEvent } from "react";
import { submitContactForm, type ContactFormCopy } from "@/lib/contact";

type FormState = {
  name: string;
  phone: string;
  email: string;
  company: string;
  message: string;
};

type FormErrors = Partial<Record<keyof FormState, string>>;

type Props = {
  copy: ContactFormCopy;
};

const emptyForm: FormState = {
  name: "",
  phone: "",
  email: "",
  company: "",
  message: "",
};

function isValidEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

function isValidPhoneCn(value: string): boolean {
  const digits = value.replace(/\D/g, "");
  const normalized =
    digits.length === 13 && digits.startsWith("86") ? digits.slice(2) : digits;
  return normalized.length === 11 && normalized.startsWith("1");
}

function validateForm(values: FormState, copy: ContactFormCopy): FormErrors {
  const errors: FormErrors = {};
  if (!values.name.trim()) errors.name = copy.nameError;
  if (!values.phone.trim() || !isValidPhoneCn(values.phone)) errors.phone = copy.phoneError;
  if (!values.email.trim() || !isValidEmail(values.email)) errors.email = copy.emailError;
  if (!values.company.trim()) errors.company = copy.companyError;
  return errors;
}

function FieldError({ id, message }: { id: string; message?: string }) {
  return (
    <p id={id} className="contact-error contact-error-slot" aria-live="polite" aria-hidden={!message}>
      {message ?? ""}
    </p>
  );
}

export default function ContactForm({ copy }: Props) {
  const [values, setValues] = useState<FormState>(emptyForm);
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  function updateField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setValues((current) => ({ ...current, [key]: value }));
    if (submitError) setSubmitError(null);
    if (errors[key]) {
      setErrors((current) => {
        const next = { ...current };
        delete next[key];
        return next;
      });
    }
  }

  async function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitted(false);

    const nextErrors = validateForm(values, copy);
    if (Object.keys(nextErrors).length > 0) {
      setErrors(nextErrors);
      return;
    }

    setSubmitting(true);
    setSubmitError(null);

    const result = await submitContactForm({
      name: values.name.trim(),
      phone: values.phone.trim(),
      email: values.email.trim(),
      company: values.company.trim(),
      message: values.message.trim(),
    });

    setSubmitting(false);

    if (!result.ok) {
      setSubmitError(result.error || copy.submitError);
      return;
    }

    setValues(emptyForm);
    setErrors({});
    setSubmitted(true);
  }

  const footerMessage = submitted
    ? copy.successDescription
    : submitError ?? copy.footerNote;

  const footerClassName = submitted
    ? "contact-form-note contact-form-note--success"
    : submitError
      ? "contact-form-note contact-form-note--error"
      : "contact-form-note";

  return (
    <form className="contact-form" noValidate onSubmit={handleSubmit}>
      <div className="contact-form-grid">
        <div className="contact-field">
          <label className="contact-label" htmlFor="contact-name">
            {copy.nameLabel}
          </label>
          <div className="contact-control">
            <input
              id="contact-name"
              className="contact-input"
              type="text"
              autoComplete="name"
              value={values.name}
              placeholder={copy.namePlaceholder}
              aria-invalid={Boolean(errors.name)}
              aria-describedby={errors.name ? "contact-name-error" : undefined}
              disabled={submitting}
              onChange={(event) => updateField("name", event.target.value)}
            />
            <FieldError id="contact-name-error" message={errors.name} />
          </div>
        </div>

        <div className="contact-field">
          <label className="contact-label" htmlFor="contact-phone">
            {copy.phoneLabel}
          </label>
          <div className="contact-control">
            <input
              id="contact-phone"
              className="contact-input"
              type="tel"
              autoComplete="tel"
              inputMode="tel"
              value={values.phone}
              placeholder={copy.phonePlaceholder}
              aria-invalid={Boolean(errors.phone)}
              aria-describedby={errors.phone ? "contact-phone-error" : undefined}
              disabled={submitting}
              onChange={(event) => updateField("phone", event.target.value)}
            />
            <FieldError id="contact-phone-error" message={errors.phone} />
          </div>
        </div>
      </div>

      <div className="contact-field">
        <label className="contact-label" htmlFor="contact-email">
          {copy.emailLabel}
        </label>
        <div className="contact-control">
          <input
            id="contact-email"
            className="contact-input"
            type="email"
            autoComplete="email"
            value={values.email}
            placeholder={copy.emailPlaceholder}
            aria-invalid={Boolean(errors.email)}
            aria-describedby={errors.email ? "contact-email-error" : undefined}
            disabled={submitting}
            onChange={(event) => updateField("email", event.target.value)}
          />
          <FieldError id="contact-email-error" message={errors.email} />
        </div>
      </div>

      <div className="contact-field">
        <label className="contact-label" htmlFor="contact-company">
          {copy.companyLabel}
        </label>
        <div className="contact-control">
          <input
            id="contact-company"
            className="contact-input"
            type="text"
            autoComplete="organization"
            value={values.company}
            placeholder={copy.companyPlaceholder}
            aria-invalid={Boolean(errors.company)}
            aria-describedby={errors.company ? "contact-company-error" : undefined}
            disabled={submitting}
            onChange={(event) => updateField("company", event.target.value)}
          />
          <FieldError id="contact-company-error" message={errors.company} />
        </div>
      </div>

      <div className="contact-field">
        <label className="contact-label" htmlFor="contact-message">
          {copy.messageLabel}
        </label>
        <div className="contact-textarea-wrap">
          <textarea
            id="contact-message"
            className="contact-textarea"
            rows={4}
            maxLength={copy.messageMaxLength}
            value={values.message}
            placeholder={copy.messagePlaceholder}
            disabled={submitting}
            onChange={(event) => updateField("message", event.target.value)}
          />
          <div className="contact-textarea-count" aria-live="polite">
            {values.message.length}/{copy.messageMaxLength}
          </div>
        </div>
      </div>

      <div className="contact-form-actions">
        <button
          className="btn btn-primary contact-submit"
          type="submit"
          disabled={submitting}
        >
          <span>{submitting ? copy.submittingLabel : copy.submitLabel}</span>
          <ArrowRight size={16} aria-hidden="true" />
        </button>
        <p
          className={footerClassName}
          role={submitted ? "status" : submitError ? "alert" : undefined}
          aria-live="polite"
        >
          {footerMessage}
        </p>
      </div>
    </form>
  );
}
