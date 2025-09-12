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
      <Row>
        {charts.map((chart, index) => (
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