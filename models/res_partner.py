from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = "res.partner"


    def _is_institution(self):
        """
        This a method to check if the partner in question is of the institution type and therefore exempt from order
        line splitting based on the fore-casted delivery date

        :return: Boolean value whether the agent is exempted from split Sale Orders
        """
        # TODO - implement the actual method in a more robust way
        self.ensure_one()
        institutional_agent_type = self.env["agent.type"].search([(
            "name", "in", ("Institutions", "Institution")
        )], limit=0)

        if not institutional_agent_type.exists():
            return False

        return self.agent_type_id.id == institutional_agent_type.id and self.agent_type_id.split_exempt


ResPartner()
