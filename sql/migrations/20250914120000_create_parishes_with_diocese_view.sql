CREATE OR REPLACE VIEW parishes_with_diocese_name AS
SELECT
    p.*,
    d."Name" AS diocese_name
FROM
    "public"."Parishes" p
JOIN
    "public"."Dioceses" d ON p.diocese_id = d.id;