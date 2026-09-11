devrelease_ps:
	$$tag="dev-$$(git rev-parse HEAD)"
	git tag $$tag
	git push --tags
	gh release create $$tag --notes "development release" --latest=false