from playwright.sync_api import sync_playwright
from app.browser.field_mapper import FieldMapper
import time
import os
import json
from datetime import datetime
import shutil

class BrowserApplicationAgent:
    def __init__(self, application, candidate, job, profile, resume_path, target_url=None):
        self.application = application
        self.candidate = candidate
        self.job = job
        self.profile = profile
        self.resume_path = resume_path
        self.mapper = FieldMapper(candidate, profile, application, resume_path)
        self.target_url = target_url or job.job_url


    def _setup_audit_dir(self):
        base_dir = os.path.join("data", "browser_runs")
        os.makedirs(base_dir, exist_ok=True)
        
        # Cleanup old runs (keep latest 20)
        runs = []
        for d in os.listdir(base_dir):
            p = os.path.join(base_dir, d)
            if os.path.isdir(p):
                runs.append((p, os.path.getctime(p)))
        runs.sort(key=lambda x: x[1], reverse=True)
        if len(runs) > 20:
            for p, _ in runs[20:]:
                try:
                    shutil.rmtree(p)
                except:
                    pass
                    
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = os.path.join(base_dir, f"app_{self.application.id}_{ts}")
        os.makedirs(run_dir, exist_ok=True)
        return run_dir



    def _setup_submission_audit_dir(self):
        base_dir = os.path.join("data", "browser_submissions")
        os.makedirs(base_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = os.path.join(base_dir, f"app_{self.application.id}_{ts}")
        os.makedirs(run_dir, exist_ok=True)
        return run_dir

    def run_dry_run(self):
        audit_dir = self._setup_audit_dir()
        screenshot_path = os.path.join(audit_dir, "screenshot.png")
        html_path = os.path.join(audit_dir, "page.html")
        report_path = os.path.join(audit_dir, "report.json")
        
        report = {
            "status": "UNKNOWN",
            "target_url": self.target_url,
            "final_url": None,
            "page_title": None,
            "audit_dir": os.path.abspath(audit_dir),
            "screenshot_path": os.path.abspath(screenshot_path),
            "page_html_path": os.path.abspath(html_path),
            "report_path": os.path.abspath(report_path),
            "fields_detected": [],
            "fields_filled": [],
            "fields_skipped": [],
            "unknown_fields": [],
            "user_input_required": [],
            "unsafe_to_autofill": [],
            "resume_uploaded": False,
            "submit_clicked": False,
            "sensitive_fields_detected": [],
            "safe_sensitive_autofill": False,
            "captcha_detected": False,
            "submission_blocked": True
        }

        def finalize_audit(page):
            try:
                page.screenshot(path=screenshot_path, full_page=True)
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(page.content())
            except:
                pass
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            
            try:
                page.goto(self.target_url, timeout=30000)
                page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception as e:
                pass # Continue anyway, the DOM might be ready enough
                
            report["final_url"] = page.url
            report["page_title"] = page.title()
            
            content = page.content().lower()
            
            # 4. Human intervention detection
            human_checks = ["security check", "cloudflare", "verify you are human", "hcaptcha"]
            if any(check in content for check in human_checks):
                report["status"] = "HUMAN_INTERVENTION_REQUIRED"
                finalize_audit(page)
                browser.close()
                return report
                
            captcha_checks = ["captcha", "recaptcha", "hcaptcha"]
            if any(check in content for check in captcha_checks):
                report["captcha_detected"] = True
                # In DRY RUN, we continue to inspect. In submission, this would force HUMAN_INTERVENTION_REQUIRED.
                
            login_checks = ["sign in", "login", "log in", "password", "mfa", "otp", "verification code"]
            if any(check in content for check in login_checks):
                # Extra safety: check if there's an actual password input
                if page.locator("input[type='password']").count() > 0:
                    report["status"] = "LOGIN_REQUIRED"
                    finalize_audit(page)
                    browser.close()
                    return report
                
            try:
                page.wait_for_selector("input", timeout=5000)
            except:
                pass
                
            inputs = page.locator("input, textarea, select")
            count = inputs.count()
            
            if count == 0:
                report["status"] = "FORM_NOT_FOUND"
                finalize_audit(page)
                browser.close()
                return report
                
            report["status"] = "DRY_RUN_READY"
            
            for i in range(count):
                el = inputs.nth(i)
                
                try:
                    if not el.is_visible():
                        continue
                except:
                    continue
                    
                field_type = el.get_attribute("type") or el.evaluate("el => el.tagName").lower()
                
                # MUST NOT click submit!
                if field_type in ["hidden", "submit", "button", "image"]:
                    continue
                    
                input_id = el.get_attribute("id") or ""
                name_attr = el.get_attribute("name") or ""
                placeholder = el.get_attribute("placeholder") or ""
                
                label_text = ""
                if input_id:
                    label = page.locator(f"label[for='{input_id}']")
                    if label.count() > 0:
                        label_text = label.first.inner_text()
                        
                # 5. Field Mapping
                value, status = self.mapper.resolve_field(
                    field_label=label_text,
                    field_type=field_type,
                    input_id=input_id,
                    name_attr=name_attr,
                    placeholder=placeholder
                )
                
                field_summary = {
                    "type": field_type,
                    "id": input_id,
                    "name": name_attr,
                    "label": label_text,
                    "placeholder": placeholder,
                    "confidence": status,
                    "source_value_used": bool(value)
                }
                report["fields_detected"].append(field_summary)
                
                if status == "KNOWN" and value:
                    try:
                        if field_type == "file":
                            if self.resume_path:
                                el.set_input_files(self.resume_path)
                                report["resume_uploaded"] = True
                                report["fields_filled"].append(field_summary)
                        elif el.evaluate("el => el.tagName").lower() == "select":
                            el.select_option(label=str(value), timeout=1000)
                            report["fields_filled"].append(field_summary)
                        elif field_type in ["checkbox", "radio"]:
                            val_lower = str(value).lower()
                            el_val = (el.get_attribute("value") or "").lower()
                            
                            should_check = False
                            if el_val and (el_val == val_lower or el_val in val_lower.split()):
                                should_check = True
                            elif label_text and label_text.lower() in val_lower:
                                should_check = True
                            elif field_type == "checkbox" and val_lower in ["yes", "true", "1", "on"]:
                                should_check = True
                                
                            if should_check:
                                el.check()
                                report["fields_filled"].append(field_summary)
                            else:
                                if field_type == "checkbox":
                                    el.uncheck()
                                report["fields_skipped"].append(field_summary)
                        else:
                            # Use fill instead of pressSequentially to avoid accidently triggering Enter
                            el.fill(str(value))
                            report["fields_filled"].append(field_summary)
                    except Exception as e:
                        print(f"Could not fill {name_attr}: {e}")
                        report["fields_skipped"].append(field_summary)
                elif status == "USER_INPUT_REQUIRED":
                    report["user_input_required"].append(field_summary)
                elif status == "UNSAFE_TO_AUTOFILL":
                    report["unsafe_to_autofill"].append(field_summary)
                elif status == "SENSITIVE_DEMOGRAPHIC":
                    field_summary["confidence"] = "USER_INPUT_REQUIRED"
                    report["user_input_required"].append(field_summary)
                    report["sensitive_fields_detected"].append({
                        "label": label_text or name_attr or input_id,
                        "category": "SENSITIVE_DEMOGRAPHIC",
                        "decision": "USER_INPUT_REQUIRED"
                    })
                else:
                    report["unknown_fields"].append(field_summary)
                    
            # 3. Browser safety - GUARANTEE NO SUBMIT
            report["submit_clicked"] = False
            
            time.sleep(1)
            finalize_audit(page)
            browser.close()
            
        return report

    def submit_application(self, db):
        self.application.submission_started_at = datetime.utcnow()
        db.commit()
        
        audit_dir = self._setup_submission_audit_dir()
        before_screenshot = os.path.join(audit_dir, "before_submit.png")
        after_screenshot = os.path.join(audit_dir, "after_submit.png")
        html_path = os.path.join(audit_dir, "final_page.html")
        report_path = os.path.join(audit_dir, "report.json")
        
        report = {
            "status": "UNKNOWN",
            "target_url": self.target_url,
            "final_url": None,
            "page_title": None,
            "fields_filled": [],
            "resume_uploaded": False,
            "submit_clicked": False,
            "error": None
        }

        def finalize_audit(page, is_after=False):
            try:
                page.screenshot(path=after_screenshot if is_after else before_screenshot, full_page=True)
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(page.content())
            except:
                pass
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)

        def mark_failed(status, error_msg):
            report["status"] = status
            report["error"] = error_msg
            self.application.status = status
            self.application.submission_error = error_msg
            db.commit()
            return report

        # Preflight Check 1: Base existence
        if not self.candidate or not self.job or not self.profile or not self.resume_path:
            return mark_failed("BLOCKED", "Missing prerequisite components (resume, profile, etc.)")
            
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            
            try:
                page.goto(self.target_url, timeout=30000)
                page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception as e:
                pass
                
            report["final_url"] = page.url
            report["page_title"] = page.title()
            
            content = page.content().lower()
            
            human_checks = ["security check", "cloudflare", "verify you are human", "hcaptcha", "captcha", "recaptcha"]
            if any(check in content for check in human_checks):
                finalize_audit(page)
                browser.close()
                return mark_failed("HUMAN_INTERVENTION_REQUIRED", "CAPTCHA or anti-bot challenge detected")
                
            login_checks = ["sign in", "login", "log in", "password", "mfa", "otp", "verification code"]
            if any(check in content for check in login_checks):
                if page.locator("input[type='password']").count() > 0:
                    finalize_audit(page)
                    browser.close()
                    return mark_failed("LOGIN_REQUIRED", "Authentication wall detected")
                    
            try:
                page.wait_for_selector("input", timeout=5000)
            except:
                pass
                
            inputs = page.locator("input, textarea, select")
            count = inputs.count()
            
            if count == 0:
                finalize_audit(page)
                browser.close()
                return mark_failed("FORM_NOT_FOUND", "No form inputs found on the page")
                
            # Fill form
            for i in range(count):
                el = inputs.nth(i)
                try:
                    if not el.is_visible():
                        continue
                except:
                    continue
                    
                field_type = el.get_attribute("type") or el.evaluate("el => el.tagName").lower()
                
                if field_type in ["hidden", "submit", "button", "image"]:
                    continue
                    
                input_id = el.get_attribute("id") or ""
                name_attr = el.get_attribute("name") or ""
                placeholder = el.get_attribute("placeholder") or ""
                is_required = el.get_attribute("required") is not None
                
                label_text = ""
                if input_id:
                    label = page.locator(f"label[for='{input_id}']")
                    if label.count() > 0:
                        label_text = label.first.inner_text()
                        
                value, status = self.mapper.resolve_field(
                    field_label=label_text,
                    field_type=field_type,
                    input_id=input_id,
                    name_attr=name_attr,
                    placeholder=placeholder
                )
                
                if status == "KNOWN" and value:
                    try:
                        if field_type == "file":
                            el.set_input_files(self.resume_path)
                            report["resume_uploaded"] = True
                            report["fields_filled"].append(name_attr or input_id)
                        elif el.evaluate("el => el.tagName").lower() == "select":
                            el.select_option(label=str(value), timeout=1000)
                            report["fields_filled"].append(name_attr or input_id)
                        elif field_type in ["checkbox", "radio"]:
                            val_lower = str(value).lower()
                            el_val = (el.get_attribute("value") or "").lower()
                            
                            should_check = False
                            if el_val and (el_val == val_lower or el_val in val_lower.split()):
                                should_check = True
                            elif label_text and label_text.lower() in val_lower:
                                should_check = True
                            elif field_type == "checkbox" and val_lower in ["yes", "true", "1", "on"]:
                                should_check = True
                                
                            if should_check:
                                el.check()
                                report["fields_filled"].append(name_attr or input_id)
                            else:
                                if field_type == "checkbox":
                                    el.uncheck()
                        else:
                            el.fill(str(value))
                            report["fields_filled"].append(name_attr or input_id)
                    except Exception as e:
                        print(f"Could not fill {name_attr}: {e}")
                else:
                    if is_required:
                        finalize_audit(page)
                        browser.close()
                        return mark_failed("BLOCKED", f"Missing required field: {name_attr or input_id} ({status})")
                        
            # Final submit
            finalize_audit(page, is_after=False)
            
            submit_btn = page.locator("input[type='submit'], button[type='submit'], button:has-text('Submit'), button:has-text('Apply')")
            if submit_btn.count() > 0:
                try:
                    submit_btn.first.click()
                    report["submit_clicked"] = True
                    # Wait for navigation
                    page.wait_for_load_state("domcontentloaded", timeout=10000)
                    time.sleep(2) # Give it a moment to show success message
                    
                    report["status"] = "SUBMITTED"
                    report["final_url"] = page.url
                    self.application.status = "SUBMITTED"
                    self.application.submitted_at = datetime.utcnow()
                    self.application.submitted_url = page.url
                    self.application.submission_result = "Submission executed successfully"
                    db.commit()
                except Exception as e:
                    report["status"] = "SUBMISSION_FAILED"
                    report["error"] = str(e)
                    self.application.status = "SUBMISSION_FAILED"
                    self.application.submission_error = str(e)
                    db.commit()
            else:
                report["status"] = "SUBMISSION_FAILED"
                report["error"] = "No submit button found"
                self.application.status = "SUBMISSION_FAILED"
                self.application.submission_error = "No submit button found"
                db.commit()
                
            finalize_audit(page, is_after=True)
            browser.close()
            
        return report

