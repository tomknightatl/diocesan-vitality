import { Container, Row, Col, Card } from "react-bootstrap";

function Reports() {
  // Get API URL from environment variable, fallback to localhost for development
  const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

  const charts = [
    {
      file: "dioceses_records_over_time.png",
      title: "Dioceses Records Over Time",
      description: "Number of diocese records added to the database over time",
    },
    {
      file: "diocesesparishdirectory_records_over_time.png",
      title: "Diocese Parish Directory Records Over Time",
      description:
        "Number of diocese parish directory records processed over time",
    },
    {
      file: "parishes_records_over_time.png",
      title: "Parishes Records Over Time",
      description:
        "Number of parish records extracted and added to the database over time",
    },
    {
      file: "parishdata_records_over_time.png",
      title: "Parish Data Records Over Time",
      description: "Number of parish data records extracted over time",
    },
  ];

  return (
    <Container className="mt-4">
      <h3 className="mb-3">Diocese Data</h3>
      <Row className="mb-5">
        {charts.slice(0, 2).map((chart, index) => (
          <Col key={index} md={6} className="mb-4">
            <Card className="h-100">
              <Card.Body className="p-2">
                <img
                  src={`${apiUrl}/api/charts/${chart.file}`}
                  alt={chart.title}
                  className="img-fluid w-100"
                  style={{ maxHeight: "300px", objectFit: "contain" }}
                  onError={(e) => {
                    e.target.onerror = null;
                    e.target.src = `/${chart.file}`; // Fallback to static file for local development
                  }}
                />
              </Card.Body>
            </Card>
          </Col>
        ))}
      </Row>

      <h3 className="mb-3">Parish Data</h3>
      <Row>
        {charts.slice(2, 4).map((chart, index) => (
          <Col key={index} md={6} className="mb-4">
            <Card className="h-100">
              <Card.Body className="p-2">
                <img
                  src={`${apiUrl}/api/charts/${chart.file}`}
                  alt={chart.title}
                  className="img-fluid w-100"
                  style={{ maxHeight: "300px", objectFit: "contain" }}
                  onError={(e) => {
                    e.target.onerror = null;
                    e.target.src = `/${chart.file}`; // Fallback to static file for local development
                  }}
                />
              </Card.Body>
            </Card>
          </Col>
        ))}
      </Row>
    </Container>
  );
}

export default Reports;
