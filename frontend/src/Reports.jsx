import { Container, Row, Col, Card } from 'react-bootstrap';

function Reports() {
  const charts = [
    'dioceses_records_over_time.png',
    'diocesesparishdirectory_records_over_time.png',
    'parishes_records_over_time.png',
    'parishschedules_records_over_time.png'
  ];

  return (
    <Container className="mt-4">
      <h2>Reports</h2>

      <h1>Diocese Data</h1>
      <Row>
        {charts.slice(0, 2).map((chart, index) => (
          <Col key={index} md={6} className="mb-4">
            <Card>
              <Card.Img variant="top" src={`/${chart}`} />
            </Card>
          </Col>
        ))}
      </Row>

      <h1>Parish Data</h1>
      <Row>
        {charts.slice(2, 4).map((chart, index) => (
          <Col key={index} md={6} className="mb-4">
            <Card>
              <Card.Img variant="top" src={`/${chart}`} />
            </Card>
          </Col>
        ))}
      </Row>
    </Container>
  );
}

export default Reports;