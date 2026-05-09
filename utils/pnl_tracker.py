# # utils/pnl_tracker.py
#
# import csv
# import os
#
#
# class PnLTracker:
#     def __init__(self, filename="pnl.csv"):
#         self.filename = filename
#         self.initialized = False
#
#     def _init_file(self):
#         os.makedirs(os.path.dirname(self.filename), exist_ok=True) \
#             if "/" in self.filename else None
#
#         with open(self.filename, "w", newline="") as f:
#             writer = csv.writer(f)
#             writer.writerow([
#                 "time",
#                 "agent_id",
#                 "spot",
#                 "rv",
#                 "inventory_spot",
#                 "delta_total",
#                 "pnl_option",
#                 "pnl_hedge",
#                 "pnl_total"
#             ])
#         self.initialized = True
#
#     def log(self, t, agent, spot, rv, total_delta):
#         if not self.initialized:
#             self._init_file()
#
#         with open(self.filename, "a", newline="") as f:
#             writer = csv.writer(f)
#             writer.writerow([
#                 t,
#                 agent.id,
#                 spot,
#                 rv,
#                 agent.inventory,
#                 total_delta,
#                 agent.pnl_option,
#                 agent.pnl_hedge,
#                 agent.total_pnl
#             ])
