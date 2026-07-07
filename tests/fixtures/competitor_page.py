"""Realistic competitor HTML pages for integration testing."""

# A home services company homepage exercising all 12+ parsing strategies
HOME_SERVICES_HOMEPAGE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <title>ABC Home Services | Plumbing, Electrical & HVAC</title>
    <meta name="description" content="ABC Home Services offers professional plumbing, electrical, and HVAC services across 50+ cities." />
    <meta name="keywords" content="plumbing, electrical, HVAC, home services, repair" />
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "HomeAndConstructionBusiness",
        "name": "ABC Home Services",
        "description": "Professional home services since 1995",
        "url": "https://abchomeservices.example.com",
        "logo": "https://abchomeservices.example.com/logo.png",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": "123 Main St",
            "addressLocality": "Springfield",
            "addressRegion": "IL",
            "postalCode": "62701"
        },
        "contactPoint": {
            "@type": "ContactPoint",
            "telephone": "+1-800-555-0199",
            "contactType": "customer service",
            "email": "contact@abchomeservices.example.com"
        }
    }
    </script>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "item": {"@id": "https://abchomeservices.example.com", "name": "Home"}},
            {"@type": "ListItem", "position": 2, "item": {"@id": "https://abchomeservices.example.com/services", "name": "Services"}},
            {"@type": "ListItem", "position": 3, "item": {"@id": "https://abchomeservices.example.com/plumbing", "name": "Plumbing"}}
        ]
    }
    </script>
</head>
<body>
    <header>
        <nav aria-label="Main navigation">
            <a href="/">Home</a>
            <a href="/services">Services</a>
            <a href="/pricing">Pricing</a>
            <a href="/about">About</a>
            <a href="/contact">Contact</a>
        </nav>
    </header>

    <main>
        <section id="services">
            <h2>Our Services</h2>
            <table>
                <caption>Service Pricing</caption>
                <thead>
                    <tr>
                        <th>Service</th>
                        <th>Description</th>
                        <th>Price</th>
                        <th>Duration</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Drain Cleaning</td>
                        <td>Professional drain cleaning service</td>
                        <td>$149</td>
                        <td>1 hour</td>
                    </tr>
                    <tr>
                        <td>Water Heater Repair</td>
                        <td>Expert water heater repair</td>
                        <td>$249</td>
                        <td>2 hours</td>
                    </tr>
                    <tr>
                        <td>Electrical Wiring</td>
                        <td>Complete electrical wiring service</td>
                        <td>$399</td>
                        <td>4 hours</td>
                    </tr>
                </tbody>
            </table>
        </section>

        <section id="faq">
            <h2>Frequently Asked Questions</h2>
            <details>
                <summary>What plumbing services do you offer?</summary>
                <p>We offer comprehensive plumbing services including drain cleaning, water heater repair, and pipe installation.</p>
            </details>
            <details>
                <summary>How much does HVAC maintenance cost?</summary>
                <p>Our HVAC maintenance starts at $99 per visit. Annual plans are available for $299.</p>
            </details>
            <details>
                <summary>What areas do you serve?</summary>
                <p>We serve Springfield, Decatur, Champaign, Bloomington, and Peoria.</p>
            </details>
        </section>

        <section id="contact">
            <h2>Contact Us</h2>
            <form action="/submit" method="post">
                <label for="name">Full Name:</label>
                <input type="text" id="name" name="name" required />

                <label for="email">Email Address:</label>
                <input type="email" id="email" name="email" placeholder="you@example.com" />

                <label for="phone">Phone Number:</label>
                <input type="tel" id="phone" name="phone" placeholder="555-0123" />

                <label for="service-type">Service Needed:</label>
                <select id="service-type" name="service_type">
                    <option value="">Select a service...</option>
                    <option value="plumbing">Plumbing</option>
                    <option value="electrical">Electrical</option>
                    <option value="hvac">HVAC</option>
                    <option value="general">General Handyman</option>
                </select>

                <label for="city">Your City:</label>
                <select id="city" name="city">
                    <option value="springfield">Springfield</option>
                    <option value="decatur">Decatur</option>
                    <option value="champaign">Champaign</option>
                </select>

                <button type="submit">Send Request</button>
            </form>
        </section>

        <section itemscope itemtype="https://schema.org/FAQPage">
            <h2>Schema.org FAQ</h2>
            <div itemprop="mainEntity" itemscope itemtype="https://schema.org/Question">
                <h3 itemprop="name">Do you offer emergency services?</h3>
                <div itemprop="acceptedAnswer" itemscope itemtype="https://schema.org/Answer">
                    <div itemprop="text">Yes, we offer 24/7 emergency plumbing and electrical services.</div>
                </div>
            </div>
        </section>

        <section itemscope itemtype="https://schema.org/Product">
            <h2>Service Plans</h2>
            <div itemprop="offers" itemscope itemtype="https://schema.org/Offer">
                <meta itemprop="name" content="Basic Plan" />
                <span itemprop="price" content="19.99">$19.99</span>
                <span itemprop="priceCurrency" content="USD">USD</span>
                <span itemprop="description">Monthly maintenance plan</span>
            </div>
            <div itemprop="offers" itemscope itemtype="https://schema.org/Offer">
                <meta itemprop="name" content="Premium Plan" />
                <span itemprop="price" content="49.99">$49.99</span>
                <span itemprop="priceCurrency" content="USD">USD</span>
                <span itemprop="description">Full coverage plan with priority service</span>
            </div>
        </section>
    </main>

    <footer>
        <p>&copy; 2026 ABC Home Services</p>
        <div>
            <a href="https://facebook.com/abchomeservices">Facebook</a>
            <a href="https://linkedin.com/company/abchomeservices">LinkedIn</a>
            <a href="https://instagram.com/abchomeservices">Instagram</a>
        </div>
        <nav aria-label="Footer">
            <a href="/privacy">Privacy Policy</a>
            <a href="/terms">Terms of Service</a>
        </nav>
    </footer>
</body>
</html>
"""
