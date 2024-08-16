Have added a new custom Solr field type that is very similar to the existing string type but allows for
case-insensitive matching. Intended for key fields like Reference Numbers or other identifiers.

The following Custom Search Fields were updated:

 - QP Notes: reference_number
 - Briefing Titles: tracking_number
 - Travel: ref_number
 - Grants: 	recipient_legal_name,
            recipient_country,
            ref_number,
            recipient_postal_code,
            recipient_city_en,
            recipient_city_fr,
            naics_identifier


