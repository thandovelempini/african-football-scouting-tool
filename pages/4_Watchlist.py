import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app_data import ROLE_LABELS, cards, footer, hero, load_percentiles, style  # noqa: E402
from config import CURRENT_SEASON, PROFILE_SEASONS  # noqa: E402
from watchlist import STATUSES, load, merge, save  # noqa: E402

st.set_page_config(page_title="Watchlist", page_icon=":material/bookmarks:", layout="wide")
style()

hero("Watchlist",
     "Players you're following up, with where they stand and why",
     kicker=f"Betway Premiership · {min(PROFILE_SEASONS)} to {CURRENT_SEASON}")

wl = load()

if wl.empty:
    st.info("Your watchlist is empty. Add players with the **Add to watchlist** button on the "
            "Shortlist, Player profile or Compare pages.")
    st.page_link("pages/1_Shortlist.py", label="Build a shortlist",
                  icon=":material/format_list_numbered:")
else:
    counts = wl["status"].value_counts()
    cards([(s, str(counts.get(s, 0)), "") for s in STATUSES])

    pct = load_percentiles()
    ages = pct.drop_duplicates("player_id").set_index("player_id")["Age"]

    show = st.segmented_control("Show", ["All"] + STATUSES, default="All") or "All"
    view = wl if show == "All" else wl[wl["status"] == show]
    view = view.assign(
        Age=view["player_id"].map(ages),
        Role=view["role"].map(lambda r: ROLE_LABELS.get(r, r)),
        Player=("Player_Profile?player=" + view["player_id"] + "&season=" + view["season"]
                + "#" + view["Player"]),
        Remove=False,
    )

    edited = st.data_editor(
        view[["Player", "Squad", "Role", "Age", "season", "status", "note",
              "added", "Remove"]],
        hide_index=True, use_container_width=True, key=f"watchlist_{show}",
        disabled=["Squad", "Role", "Age", "season", "added"],
        column_config={
            "Squad": "Club",
            "Age": st.column_config.NumberColumn("Age", format="%d", width=60),
            "season": st.column_config.TextColumn("Season", width=90),
            "status": st.column_config.SelectboxColumn("Status", options=STATUSES,
                                                       required=True, width=130),
            "note": st.column_config.TextColumn("Note", width=300,
                                                help="Why they're here, what to check next"),
            "added": st.column_config.TextColumn("Added", width=100),
            "Player": st.column_config.LinkColumn("Player", display_text=r"#(.+)$",
                                                  width="medium"),
            "Remove": st.column_config.CheckboxColumn("Drop", width=80,
                                                      help="Tick, then press Remove below"),
        },
    )

    changed = (edited["status"].values != view["status"].values) | \
              (edited["note"].fillna("").values != view["note"].fillna("").values)
    if changed.any():
        for idx, status, note in zip(view.index[changed], edited["status"][changed],
                                     edited["note"][changed]):
            wl.loc[idx, ["status", "note"]] = [status, note or ""]
        save(wl)
        st.toast("Watchlist saved", icon=":material/check:")

    ticked = view.index[edited["Remove"].values]
    if len(ticked):
        if st.button(f"Remove {len(ticked)} ticked", icon=":material/delete:", type="primary"):
            save(wl.drop(index=ticked))
            st.rerun()

    st.download_button("Download watchlist (CSV)", wl.to_csv(index=False),
                       file_name="watchlist.csv", mime="text/csv",
                       icon=":material/download:")

with st.expander("Load a saved watchlist"):
    st.caption("Adds players from a watchlist CSV you downloaded earlier. "
               "Players already on your list are kept as they are.")
    upload = st.file_uploader("Watchlist CSV", type="csv", label_visibility="collapsed")
    if upload is not None and st.button("Load", icon=":material/upload:"):
        try:
            added = merge(pd.read_csv(upload, dtype={"player_id": str}))
            st.success(f"Added {added} player{'s' if added != 1 else ''}.")
            st.rerun()
        except (KeyError, ValueError, pd.errors.ParserError):
            st.error("That file doesn't look like a watchlist export.")

st.caption("The watchlist is saved on the machine running the app. On the public demo it's "
           "shared and resets when the app restarts, so download a copy to keep it.")

footer()