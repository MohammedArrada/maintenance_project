import json
from multiprocessing import context
from flask import Flask, render_template, request
from flask_restx import Api, Resource

app = Flask(__name__)
api=Api(app)


valid_priorities=["LOW", "MEDIUM", "HIGH"]
valid_statuses=["OPEN", "ASSIGNED", "IN_PROGRESS", "CLOSED"]

tickets_test = [
    {"id": 1, "equipment": "Router A", "description": "Connection failure", "priority": "HIGH", "status": "OPEN", "technician": "", "resolution": ""},
    {"id": 2, "equipment": "Laptop B", "description": "Update required", "priority": "LOW", "status": "ASSIGNED", "technician": "Amina", "resolution": ""}
]
technicians_test = [
    {"name": "Amina", "active_limit": 3},
    {"name": "Karim", "active_limit": 2},
    {"name": "Sara", "active_limit": 3}
]

tickets_file = 'tickets.json'
technicians_file = 'technicians.json'
reports_file='reports.txt'
history_file='history.json'


##################  my functions    ####################################
def load_json_file(file_path):
    try:
        with open(file_path, 'r') as f:
            print(f"{file_path} loaded successfully.")
            return json.load(f)
    except FileNotFoundError:
        print(f"{file_path} not found.")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {file_path}.")
        return []



def save_json_file(file_path, data):
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
            print(f"{file_path} saved successfully.")
            return True
    except Exception as e:
        print(f"Error saving {file_path}: {e}")
        return False



def active_count(technician_name, tickets):
    count = 0
    for ticket in tickets:
        if ticket["technician"] == technician_name and ticket["status"] != "CLOSED":
            count += 1
    return count

# Before assigning:
# if active_count(name, tickets) >= technician["active_limit"]:
#     return {"message": "Technician at capacity"}, 400

#find_ticket, find_technician, active_count, assign_ticket, close_ticket, summary_report.


def find_ticket(ticket_id):
    return next((t for t in tickets if t['id'] == ticket_id), None)

def find_technician(technician_name):
    return next((tech for tech in technicians if tech['name'] == technician_name), None)

def assign_ticket(ticket_id, technician_name):
    ticket = find_ticket(ticket_id)
    technician = find_technician(technician_name)

    if not ticket:
        return {"message": "Ticket not found"}, 404
    if not technician:
        return {"message": "Technician not found"}, 404
    if active_count(technician_name, tickets) >= technician["active_limit"]:
        return {"message": "Technician at capacity"}, 400

    ticket["technician"] = technician_name
    ticket["status"] = "ASSIGNED"
    return ticket, 200


def close_ticket(ticket_id, resolution):
    ticket = find_ticket(ticket_id)
    if not ticket:
        return {"message": "Ticket not found"}, 404

    ticket["resolution"] = resolution
    if ticket["resolution"]:
        ticket["status"] = "CLOSED"
        return ticket, 200

    else:
        return {"message": "Resolution is required to close the ticket"}, 400


def summary_report(tickets):
    total_tickets = len(tickets)
    open_tickets = sum(1 for t in tickets if t['status'] == 'OPEN')
    assigned_tickets = sum(1 for t in tickets if t['status'] == 'ASSIGNED')
    in_progress_tickets = sum(1 for t in tickets if t['status'] == 'IN_PROGRESS')
    closed_tickets = sum(1 for t in tickets if t['status'] == 'CLOSED')

    return {
        "total_tickets": total_tickets,
        "open_tickets": open_tickets,
        "assigned_tickets": assigned_tickets,
        "in_progress_tickets": in_progress_tickets,
        "closed_tickets": closed_tickets,
    }

def workload_report(tickets, technicians):
    technician_workload = {tech['name']: active_count(tech['name'], tickets) for tech in technicians}
    return technician_workload

def high_priority_report(tickets):
    high_priority_tickets = [t for t in tickets if t['priority'] == 'HIGH' and t['status'] != 'CLOSED']
    return high_priority_tickets

def completed_report(tickets):
    completed_tickets = [t for t in tickets if t['status'] == 'CLOSED']
    return completed_tickets

def export_reports(reports_file, tickets, technicians):
    reports = {
        "summary": summary_report(tickets),
        "workload": workload_report(tickets, technicians),
        "high_priority": high_priority_report(tickets),
        "completed": completed_report(tickets)
    }
    if save_json_file(reports_file, reports):
        return {"message": "Reports exported successfully"}, 200
    return {"message": "Failed to export reports"}, 500


tickets = load_json_file(tickets_file)
technicians = load_json_file(technicians_file)


########################################


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", tickets=tickets, technicians=technicians, summary=summary_report(tickets), workload=workload_report(tickets, technicians), high_priority=high_priority_report(tickets), completed=completed_report(tickets))
                        
@api.route('/tickets')
class Tickets(Resource):
    def get(self):
     return tickets

    @api.param('equipment', 'The equipment name')
    @api.param('description', 'The description of the ticket')
    @api.param('priority', 'The priority of the ticket (LOW, MEDIUM, HIGH)')
    @api.param('status', 'The status of the ticket (OPEN, ASSIGNED, IN_PROGRESS, CLOSED)')
    def post(self):
        equipment = request.args.get('equipment').strip()
        description = request.args.get('description').strip()
        priority = request.args.get('priority').strip().upper()
        status = request.args.get('status').strip().upper() if request.args.get('status') else "OPEN"

        if not equipment or not description or not priority:
            return {"message": "Missing required fields"}, 400

        if priority not in valid_priorities:
            return {"message": "Invalid priority value"}, 400

        if status and status not in valid_statuses:
            return {"message": "Invalid status value"}, 400
        
        new_ticket = {
            "id": len(tickets) + 1,
            "equipment": equipment,
            "description": description,
            "priority": priority,
            "status": status,
            "technician": "",
            "resolution": ""
        }

        tickets.append(new_ticket)
        save_json_file(tickets_file, tickets)
        return new_ticket, 201



@api.route('/tickets/<int:ticket_id>')
class Ticket(Resource):
    def get(self, ticket_id):
        ticket = find_ticket(ticket_id)
        if ticket:
            return ticket
        return {"message": "Ticket not found"}, 404

    def delete(self, ticket_id):
        global tickets
        ticket = find_ticket(ticket_id)
        if ticket:
            tickets = [t for t in tickets if t['id'] != ticket_id]
            save_json_file(tickets_file, tickets)
            return {"message": "Ticket deleted successfully"}
        return {"message": "Ticket not found"}, 404



@api.route('/technicians')
class Technicians(Resource):
    def get(self):
        return technicians



    @api.param('name', 'The name of the technician')
    @api.param('active_limit', 'The active limit of the technician')
    def post(self):
        name = request.args.get('name').strip()
        active_limit = request.args.get('active_limit').strip()

        new_technician = {
            "name": name,
            "active_limit": active_limit
        }

        technicians.append(new_technician)
        save_json_file(technicians_file, technicians)
        return new_technician, 201



@api.route('/reports/summary')
class SummaryReport(Resource):
    def get(self):
        return summary_report()

@api.route('/reports/workload')
class WorkloadReport(Resource):
    def get(self):
        return workload_report()

@api.route('/reports/high-priority')
class HighPriorityReport(Resource):
    def get(self):
        return high_priority_report()

@api.route('/reports/completed')
class CompletedReport(Resource):
    def get(self):
        return completed_report()


@api.route('/history')
class History(Resource):
    def get(self):
        return history

    # GET /tickets, POST /tickets,    ---- 
    # GET /tickets/<int:ticket_id>, DELETE /tickets/<int:ticket_id>
    # GET /technicians, POST /technicians    ---
    # POST /tickets/<int:ticket_id>/assign, 
    # POST /tickets/<int:ticket_id>/start, 
    # POST /tickets/<int:ticket_id>/close
    # GET /reports/summary,    
    # GET /reports/workload, GET /reports/high-priority, 
    # GET /reports/completed, GET /history

if __name__ == '__main__':
    app.run(debug=True)