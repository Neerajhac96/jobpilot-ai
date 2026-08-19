import streamlit as st
import requests
import pandas as pd
import json

API_URL = "http://localhost:8000"

st.set_page_config(page_title="JobPilot AI Dashboard", layout="wide")

st.title("🚀 JobPilot AI Dashboard")

# 1. Overview
st.header("Overview")
stats_res = requests.get(f"{API_URL}/dashboard/stats")
if stats_res.status_code == 200:
    stats = stats_res.json()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("Jobs")
        st.metric("Total Jobs", stats["jobs"]["total"])
        st.metric("Analyzed", stats["jobs"]["analyzed"])
        st.metric("Unanalyzed", stats["jobs"]["unanalyzed"])
    with col2:
        st.subheader("Matches")
        st.metric("Strong Matches", stats["matches"]["strong"])
        st.metric("Review", stats["matches"]["review"])
        st.metric("Skip", stats["matches"]["skip"])
    with col3:
        st.subheader("Applications")
        st.metric("Total", stats["applications"]["total"])
        st.metric("Pending Approval", stats["applications"]["pending_approval"])
        st.metric("Approved", stats["applications"]["approved"])
        st.metric("Submitted", stats["applications"]["submitted"])
        st.metric("Interviewing", stats["applications"]["interview"])
        st.metric("Rejected", stats["applications"]["rejected"])

st.markdown("---")

# 4 & 5. Candidate Profile
st.header("Candidate Profile")
candidate_res = requests.get(f"{API_URL}/candidate/me")
profile_res = requests.get(f"{API_URL}/candidate/application-profile")

col1, col2 = st.columns(2)
with col1:
    st.subheader("Core Profile")
    if candidate_res.status_code == 200:
        cand = candidate_res.json()
        st.write(f"**Name:** {cand.get('name')}")
        st.write(f"**Email:** {cand.get('email')}")
        st.write(f"**Phone:** {cand.get('phone')}")
        st.write(f"**Preferred Roles:** {cand.get('preferred_roles')}")
        st.write(f"**Preferred Locations:** {cand.get('preferred_locations')}")
        with st.expander("Skills & Experience"):
            st.write("**Skills:**")
            st.write(cand.get('skills'))
            st.write("**Experience:**")
            st.write(cand.get('experience'))
    else:
        st.warning("No candidate profile found.")

with col2:
    st.subheader("Application Profile")
    if profile_res.status_code == 200:
        prof = profile_res.json()
        st.write(f"**Notice Period:** {prof.get('notice_period')}")
        st.write(f"**Work Auth:** {prof.get('work_authorization')}")
        st.write(f"**Location Pref:** {prof.get('location_preference')}")
        st.write(f"**Salary Exp:** {prof.get('salary_expectation')}")
        st.write(f"**Willing to Relocate:** {prof.get('willing_to_relocate')}")
    else:
        st.warning("No application profile found.")

st.markdown("---")

# 2. Top Job Matches
st.header("Top Job Matches")
jobs_res = requests.get(f"{API_URL}/jobs/ranked")
if jobs_res.status_code == 200:
    jobs = jobs_res.json()
    if jobs:
        df_jobs = pd.DataFrame(jobs)
        # Filters
        col1, col2, col3 = st.columns(3)
        min_score = col1.slider("Min Match Score", 0, 100, 0)
        recs = df_jobs["recommendation"].unique().tolist()
        selected_rec = col2.multiselect("Recommendation", recs, default=recs)
        
        filtered_jobs = df_jobs[
            (df_jobs["match_score"] >= min_score) & 
            (df_jobs["recommendation"].isin(selected_rec))
        ]
        
        display_cols = ["match_score", "title", "company", "location", "recommendation", "missing_skills", "job_url", "id"]
        # Only include columns that actually exist in the dataframe
        display_cols = [c for c in display_cols if c in filtered_jobs.columns]
        
        st.dataframe(filtered_jobs[display_cols].sort_values(by="match_score", ascending=False), use_container_width=True)
    else:
        st.info("No ranked jobs found.")

st.markdown("---")

# 6. Application Table & 7. Actions
st.header("Applications & Actions")

apps_res = requests.get(f"{API_URL}/applications")
if apps_res.status_code == 200:
    apps = apps_res.json()
    if apps:
        df_apps = pd.DataFrame(apps)
        st.dataframe(df_apps, use_container_width=True)
        
        st.subheader("Actions")
        app_id_to_action = st.selectbox("Select Application ID", df_apps["application_id"].tolist())
        
        col_act1, col_act2, col_act3, col_act4 = st.columns(4)
        
        if col_act1.button("Prepare Application"):
            # Get job_id for the app
            job_id = df_apps[df_apps["application_id"] == app_id_to_action]["job_id"].values[0]
            with st.spinner("Preparing..."):
                res = requests.post(f"{API_URL}/jobs/{job_id}/application/prepare")
                if res.status_code == 200:
                    st.success("Application prepared!")
                    st.rerun()
                else:
                    st.error(res.text)
                    
        if col_act2.button("Approve Application"):
            with st.spinner("Approving..."):
                res = requests.post(f"{API_URL}/applications/{app_id_to_action}/approve")
                if res.status_code == 200:
                    st.success("Approved!")
                    st.rerun()
                else:
                    st.error(res.text)
                    
        if col_act3.button("Run Dry Run"):
            with st.spinner("Running browser dry run..."):
                res = requests.post(f"{API_URL}/applications/{app_id_to_action}/dry-run")
                if res.status_code == 200:
                    st.success("Dry run completed!")
                    with st.expander("Dry Run Report"):
                        st.json(res.json())
                else:
                    st.error(res.text)
                    
        if col_act4.button("Confirm Submit"):
            st.warning("Are you sure? This will attempt real submission.")
            if st.button("Yes, actually submit"):
                with st.spinner("Submitting..."):
                    res = requests.post(f"{API_URL}/applications/{app_id_to_action}/confirm-submission", json={"confirm": True})
                    if res.status_code == 200:
                        st.success("Submission workflow finished!")
                        with st.expander("Submission Report"):
                            st.json(res.json())
                    else:
                        st.error(res.text)
    else:
        st.info("No applications found.")

st.markdown("---")
st.header("Scheduler Actions")
col1, col2 = st.columns(2)
if col1.button("Check Scheduler Status"):
    res = requests.get(f"{API_URL}/scheduler/status")
    if res.status_code == 200:
        st.json(res.json())
    else:
        st.error(res.text)

if col2.button("Run Job Hunt Now"):
    with st.spinner("Running job hunt..."):
        res = requests.post(f"{API_URL}/scheduler/run-now")
        if res.status_code == 200:
            st.success("Job hunt completed!")
            st.json(res.json())
            st.rerun()
        else:
            st.error(res.text)
