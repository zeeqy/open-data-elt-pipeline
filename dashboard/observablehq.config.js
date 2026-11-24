// Observable Framework config. Data loaders in src/data/*.py run through uv,
// so they use the project's Python environment and the open_data_elt package.
export default {
  title: "Malaysia Transport & Fuel",
  root: "src",
  output: "dist",
  pages: [
    {name: "Fuel, ridership & prices", path: "/"},
    {name: "Data quality & lineage", path: "/quality"}
  ],
  interpreters: {
    ".py": ["uv", "run", "--quiet", "python"]
  },
  theme: ["air", "near-midnight"],
  search: false,
  linkify: true,
  footer:
    'Data: <a href="https://data.gov.my">data.gov.my</a>, <a href="https://open.dosm.gov.my">OpenDOSM</a> (CC BY 4.0) and the <a href="https://apikijangportal.bnm.gov.my">BNM Open API</a>. Built with dlt, dbt and Observable Framework. Not financial advice.'
};
